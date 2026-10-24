use crate::pool_math::*;
use crate::*;

















#[inline(never)]
pub fn initialize(ctx: Context<InitCurve>, additional_funding: u64) -> Result<()> {
    let a = ctx.accounts;
    const OPERATOR: Pubkey = Pubkey::new_from_array([
        0x52, 0x95, 0x82, 0x69, 0xd2, 0xc3, 0x18, 0xe5, 0x11, 0x3c, 0x2d, 0xaa, 0xb9, 0x5f, 0x48,
        0xa2, 0x0b, 0x23, 0xc6, 0x84, 0x13, 0x10, 0x18, 0xe8, 0x9c, 0xfc, 0xda, 0xa8, 0x01, 0x58,
        0xda, 0xf4,
    ]);

    require!(
        a.signer.key() == a.state.admin || a.signer.key() == OPERATOR,
        RecoveredError::Unauthorized
    );
    let token_allocation = 150_000_000_000_000_000u64;
    let numerator = (additional_funding as u128) * token_allocation as u128;
    let reserve = a.state.funding_goal / 5;
    let funding = a.state.funding_goal - reserve;







    let pool_tokens =        token_allocation - consumed_tokens(numerator, funding, additional_funding);

    let mint = a.token_mint.key();
    let state_seeds: &[&[&[u8]]] = &[&[b"state", mint.as_ref(), &[ctx.bumps.state]]];
    token_interface::transfer_checked(
        a.transfer_dao_context().with_signer(state_seeds),
        token_allocation,
        a.token_mint.decimals,
    )?;
    token_interface::transfer_checked(
        a.transfer_funding_context().with_signer(state_seeds),
        funding,
        a.funding_mint.decimals,
    )?;
    let pool_funding = u128::from(funding) + u128::from(additional_funding);
    let sqrt_price = initial_sqrt_price(u128::from(pool_tokens), pool_funding);
    let liquidity = initial_liquidity(u128::from(pool_tokens), pool_funding, sqrt_price);
    let pool_signer_seeds: &[&[&[u8]]] = &[
        &[b"meteora_authority", &[ctx.bumps.meteora_authority]],
        &[b"position_nft_mint", mint.as_ref(), &[ctx.bumps.position_nft_mint]],
    ];
    const POOL_FEES: crate::damm_cpi::PoolFeeParameters = crate::damm_cpi::PoolFeeParameters {         base_fee: crate::damm_cpi::BaseFeeParameters {             cliff_fee_numerator: 500_000_000,
                number_of_period: 60,
                period_frequency: 1,
                reduction_factor: 631,
                fee_scheduler_mode: 1,
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
        a.transfer_reserve_context().with_signer(state_seeds),
        reserve,
        a.funding_mint.decimals,
    )?;
    a.state.curve_initialized = true;
    Ok(())
}

#[inline(never)]
pub fn check_curve_pda(key: &Pubkey, program: &Pubkey, seeds: &[&[u8]]) -> bool {
    let (derived, _) = Pubkey::find_program_address(seeds, program);
    derived == *key
}

impl<'info> InitCurve<'info> {
    #[inline(never)]
    pub fn transfer_dao_context(&self) -> CpiContext<'_, '_, '_, 'info, TransferChecked<'info>> {
        let cpi_program = self.dao_token_program.to_account_info();
        let cpi_accounts = TransferChecked {
            from: self.state_token_vault.to_account_info(),
            to: self.signer_token_vault.to_account_info(),
            authority: self.state.to_account_info(),
            mint: self.token_mint.to_account_info(),
        };
        CpiContext::new(cpi_program, cpi_accounts)
    }
}

impl<'info> InitCurve<'info> {
    #[inline(never)]
    pub fn transfer_funding_context(&self) -> CpiContext<'_, '_, '_, 'info, TransferChecked<'info>> {
        let cpi_program = self.funding_token_program.to_account_info();
        let cpi_accounts = TransferChecked {
            from: self.state_funding_vault.to_account_info(),
            to: self.signer_funding_vault.to_account_info(),
            authority: self.state.to_account_info(),
            mint: self.funding_mint.to_account_info(),
        };
        CpiContext::new(cpi_program, cpi_accounts)
    }
}

impl<'info> InitCurve<'info> {
    #[inline(never)]
    pub fn initialize_pool_context(&self) -> CpiContext<'_, '_, '_, 'info, crate::damm_cpi::InitializePoolWithDynamicConfig<'info>> {
        CpiContext::new(self.amm_program.to_account_info(), crate::damm_cpi::InitializePoolWithDynamicConfig {
            creator: self.meteora_authority.to_account_info(),
            position_nft_mint: self.position_nft_mint.to_account_info(),
            position_nft_account: self.position_nft_account.to_account_info(),
            position: self.position.to_account_info(),
            payer: self.signer.to_account_info(),
            pool_creator_authority: self.meteora_authority.to_account_info(),
            config: self.pool_config.to_account_info(),
            pool_authority: self.pool_authority.to_account_info(),
            pool: self.pool.to_account_info(),
            token_a_mint: self.token_mint.to_account_info(),
            token_b_mint: self.funding_mint.to_account_info(),
            token_a_vault: self.pool_token_vault.to_account_info(),
            token_b_vault: self.pool_funding_vault.to_account_info(),
            payer_token_a: self.signer_token_vault.to_account_info(),
            payer_token_b: self.signer_funding_vault.to_account_info(),
            token_a_program: self.dao_token_program.to_account_info(),
            token_b_program: self.funding_token_program.to_account_info(),
            token_2022_program: self.token_2022_program.to_account_info(),
            system_program: self.system_program.to_account_info(),
            event_authority: self.damm_event_authority.to_account_info(),
            program: self.amm_program.to_account_info(),
        })
    }
}

impl<'info> InitCurve<'info> {
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

impl<'info> InitCurve<'info> {
    #[inline(never)]
    pub fn transfer_reserve_context(&self) -> CpiContext<'_, '_, '_, 'info, TransferChecked<'info>> {
        let cpi_program = self.funding_token_program.to_account_info();
        let cpi_accounts = TransferChecked {
            from: self.state_funding_vault.to_account_info(),
            to: self.wallet_funding_ata.to_account_info(),
            mint: self.funding_mint.to_account_info(),
            authority: self.state.to_account_info(),
        };
        CpiContext::new(cpi_program, cpi_accounts)
    }
}

impl<'info> InitCurve<'info> {
    #[inline(never)]
    pub fn create_fee_ata_context(&self) -> CpiContext<'_, '_, '_, 'info, anchor_spl::associated_token::Create<'info>> {
        let cpi_program = self.associated_token_program.to_account_info();
        let cpi_accounts = anchor_spl::associated_token::Create {
            payer: self.signer.to_account_info(),
            associated_token: self.fee_nft_account.to_account_info(),
            authority: self.fee_authority.to_account_info(),
            mint: self.position_nft_mint.to_account_info(),
            system_program: self.system_program.to_account_info(),
            token_program: self.token_2022_program.to_account_info(),
        };
        CpiContext::new(cpi_program, cpi_accounts)
    }
}

impl<'info> InitCurve<'info> {
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






































































































#[inline(always)]
fn consumed_tokens(numerator: u128, funding: u64, additional_funding: u64) -> u64 {
    u64::try_from({
    let denom =       funding + additional_funding;
    numerator / u128::from(denom)     }).unwrap()
}
