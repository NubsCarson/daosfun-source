use crate::pool_math::*;
use crate::*;

#[inline(never)]
pub fn migrate(ctx: Context<MigrateBondingToMeteora>) -> Result<()> {
    let a = ctx.accounts;
    let total_funding = a.hedgefun_curve.funding_amount;
    let mint = a.token_mint.key();
    let migration_seeds: &[&[&[u8]]] = &[
        &[b"state", mint.as_ref(), &[ctx.bumps.state]],
        &[b"meteora_authority", &[ctx.bumps.meteora_authority]],
    ];
    hedgefun_curve::cpi::migrate_liquidity(
        a.migrate_liquidity_context().with_signer(migration_seeds),
    )?;
    let reserve = total_funding / 5;
    let pool_funding = total_funding - reserve;
    let token_allocation = 200_000_000_000_000_000u64;
    let pool_tokens = token_allocation;
    let state_seeds: &[&[&[u8]]] = &[&[b"state", mint.as_ref(), &[ctx.bumps.state]]];
    token_interface::transfer_checked(
        a.transfer_dao_context().with_signer(state_seeds),
        token_allocation,
        a.token_mint.decimals,
    )?;
    let sqrt_price = initial_sqrt_price(u128::from(pool_tokens), u128::from(pool_funding));
    let liquidity = initial_liquidity(u128::from(pool_tokens), u128::from(pool_funding), sqrt_price);
    let pool_signer_seeds: &[&[&[u8]]] = &[
        &[b"meteora_authority", &[ctx.bumps.meteora_authority]],
        &[b"position_nft_mint", mint.as_ref(), &[ctx.bumps.position_nft_mint]],
    ];
    const POOL_FEES: crate::damm_cpi::PoolFeeParameters = crate::damm_cpi::PoolFeeParameters {         base_fee: crate::damm_cpi::BaseFeeParameters {             cliff_fee_numerator: 10_000_000,
                number_of_period: 0,
                period_frequency: 0,
                reduction_factor: 0,
                fee_scheduler_mode: 0,
            },
            // Scalar fee fields recovered from the original serializer.
            protocol_fee_percent: 20,
            partner_fee_percent: 0,
            referral_fee_percent: 20,
            dynamic_fee: None,
        };
    const POOL_PARAMS: crate::damm_cpi::InitializeCustomizablePoolParameters = crate::damm_cpi::InitializeCustomizablePoolParameters {
        pool_fees: POOL_FEES,
        sqrt_min_price: MIN_SQRT_PRICE,
        sqrt_max_price: MAX_SQRT_PRICE,
        has_alpha_vault: false,
        liquidity: 0,
        sqrt_price: 0,
        activation_type: 1,
        collect_fee_mode: 1,
        activation_point: None,
        };
    
    crate::damm_cpi::initialize_pool_with_dynamic_config(
        a.initialize_pool_context().with_signer(pool_signer_seeds),
        crate::damm_cpi::InitializeCustomizablePoolParameters { liquidity, sqrt_price, ..POOL_PARAMS },
    )?;
    let authority_seeds: &[&[&[u8]]] = &[&[b"meteora_authority", &[ctx.bumps.meteora_authority]]];
    crate::damm_cpi::permanent_lock_position(
        a.permanent_lock_position_context().with_signer(authority_seeds),
        {
            let position = ExternalPosition::try_deserialize(&mut &a.position.data.try_borrow()
                .map_err(|_| anchor_lang::solana_program::program_error::ProgramError::AccountBorrowFailed)?[..])?;

            position.unlocked_liquidity
        },
    )?;
    anchor_spl::associated_token::create(a.create_fee_ata_context())?;
    token_interface::transfer_checked(
        a.transfer_nft_context().with_signer(authority_seeds),
        1,
        0,
    )?;
    token_interface::transfer_checked(
        a.transfer_reserve_context().with_signer(authority_seeds),
        reserve,
        a.funding_mint.decimals,
    )?;
    a.state.curve_initialized = true;
    a.state.funding_goal = a.hedgefun_curve.funding_amount;
    Ok(())
}

impl<'info> MigrateBondingToMeteora<'info> {
    #[inline(never)]
    pub fn transfer_dao_context(&self) -> CpiContext<'_, '_, '_, 'info, TransferChecked<'info>> {
        let cpi_program = self.dao_token_program.to_account_info();
        let cpi_accounts = TransferChecked {
            from: self.state_token_vault.to_account_info(),
            to: self.payer_token_ata.to_account_info(),
            authority: self.state.to_account_info(),
            mint: self.token_mint.to_account_info(),
        };
        CpiContext::new(cpi_program, cpi_accounts)
    }
}

impl<'info> MigrateBondingToMeteora<'info> {
    #[inline(never)]
    pub fn initialize_pool_context(&self) -> CpiContext<'_, '_, '_, 'info, crate::damm_cpi::InitializePoolWithDynamicConfig<'info>> {
        CpiContext::new(self.amm_program.to_account_info(), crate::damm_cpi::InitializePoolWithDynamicConfig {
            creator: self.meteora_authority.to_account_info(),
            position_nft_mint: self.position_nft_mint.to_account_info(),
            position_nft_account: self.position_nft_account.to_account_info(),
            position: self.position.to_account_info(),
            payer: self.payer.to_account_info(),
            pool_creator_authority: self.meteora_authority.to_account_info(),
            config: self.pool_config.to_account_info(),
            pool_authority: self.pool_authority.to_account_info(),
            pool: self.pool.to_account_info(),
            token_a_mint: self.token_mint.to_account_info(),
            token_b_mint: self.funding_mint.to_account_info(),
            token_a_vault: self.pool_token_vault.to_account_info(),
            token_b_vault: self.pool_funding_vault.to_account_info(),
            payer_token_a: self.payer_token_ata.to_account_info(),
            payer_token_b: self.payer_funding_ata.to_account_info(),
            token_a_program: self.dao_token_program.to_account_info(),
            token_b_program: self.funding_token_program.to_account_info(),
            token_2022_program: self.token_2022_program.to_account_info(),
            system_program: self.system_program.to_account_info(),
            event_authority: self.damm_event_authority.to_account_info(),
            program: self.amm_program.to_account_info(),
        })
    }
}

impl<'info> MigrateBondingToMeteora<'info> {
    #[inline(never)]
    pub fn migrate_liquidity_context(&self) -> CpiContext<'_, '_, '_, 'info, hedgefun_curve::cpi::accounts::MigrateLiquidity<'info>> {
        CpiContext::new(self.hedgefun_curve_program.to_account_info(), hedgefun_curve::cpi::accounts::MigrateLiquidity {
            payer: self.payer.to_account_info(),
            authority: self.state.to_account_info(),
            token_mint: self.token_mint.to_account_info(),
            funding_mint: self.funding_mint.to_account_info(),
            curve: self.hedgefun_curve.to_account_info(),
            payer_funding_ata: self.payer_funding_ata.to_account_info(),
            curve_funding_vault: self.curve_funding_vault.to_account_info(),
            funding_token_program: self.funding_token_program.to_account_info(),
            associated_token_program: self.associated_token_program.to_account_info(),
        })
    }
}

impl<'info> MigrateBondingToMeteora<'info> {
    #[inline(never)]
    pub fn permanent_lock_position_context(&self) -> CpiContext<'_, '_, '_, 'info, crate::damm_cpi::PermanentLockPosition<'info>> {
        let cpi_program = self.amm_program.to_account_info();
        let cpi_accounts = crate::damm_cpi::PermanentLockPosition {
            pool: self.pool.to_account_info(),
            position: self.position.to_account_info(),
            position_nft_account: self.position_nft_account.to_account_info(),
            owner: self.meteora_authority.to_account_info(),
            event_authority: self.damm_event_authority.to_account_info(),
            program: self.amm_program.to_account_info(),
        };
        CpiContext::new(cpi_program, cpi_accounts)
    }
}

impl<'info> MigrateBondingToMeteora<'info> {
    #[inline(never)]
    pub fn transfer_reserve_context(&self) -> CpiContext<'_, '_, '_, 'info, TransferChecked<'info>> {
        let cpi_program = self.funding_token_program.to_account_info();
        let cpi_accounts = TransferChecked {
            from: self.payer_funding_ata.to_account_info(),
            to: self.wallet_funding_ata.to_account_info(),
            mint: self.funding_mint.to_account_info(),
            authority: self.payer.to_account_info(),
        };
        CpiContext::new(cpi_program, cpi_accounts)
    }
}

impl<'info> MigrateBondingToMeteora<'info> {
    #[inline(never)]
    pub fn create_fee_ata_context(&self) -> CpiContext<'_, '_, '_, 'info, anchor_spl::associated_token::Create<'info>> {
        let cpi_program = self.associated_token_program.to_account_info();
        let cpi_accounts = anchor_spl::associated_token::Create {
            payer: self.payer.to_account_info(),
            associated_token: self.fee_nft_account.to_account_info(),
            authority: self.fee_authority.to_account_info(),
            mint: self.position_nft_mint.to_account_info(),
            system_program: self.system_program.to_account_info(),
            token_program: self.token_2022_program.to_account_info(),
        };
        CpiContext::new(cpi_program, cpi_accounts)
    }
}
impl<'info> MigrateBondingToMeteora<'info> {
    #[inline(never)]
    pub fn transfer_nft_context(&self) -> CpiContext<'_, '_, '_, 'info, TransferChecked<'info>> {
        let cpi_program = self.token_2022_program.to_account_info();
        let cpi_accounts = TransferChecked {
            from: self.position_nft_account.to_account_info(),
            to: self.fee_nft_account.to_account_info(),
            mint: self.position_nft_mint.to_account_info(),
            authority: self.meteora_authority.to_account_info(),
        };
        CpiContext::new(cpi_program, cpi_accounts)
    }
}

