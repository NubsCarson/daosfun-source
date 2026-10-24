use crate::*;



























#[inline(never)]
pub fn initialize(ctx: Context<InitBondingOnMeteora>, name: String, symbol: String, uri: String) -> Result<()> {
    let expiration_timestamp = Clock::get()?.unix_timestamp + 315_360_000;
    let a = ctx.accounts;
    a.state.set_inner(State {
        admin: a.admin.key(),
        dao_mint: a.token_mint.key(),
        funding_mint: a.funding_mint.key(),
        funding_goal: 0,
        admin_closed_fund: false,
        redemption_started: false,
        expiration_timestamp,
        delegate_authorities: [None; 3],
        carry_basis: 0,
        fee_authority: a.fee_authority.key(),
        curve_initialized: false,
    });
    let seeds: &[&[&[u8]]] = &[&[b"meteora_authority", &[ctx.bumps.meteora_authority]]];
    dbc_cpi::cpi::initialize_virtual_pool_with_token2022(
        a.initialize_pool_context().with_signer(seeds),
        dbc_cpi::InitializePoolParameters { name, symbol, uri },
    )?;
    let new_authority = spl_pod::optional_keys::OptionalNonZeroPubkey(a.state.key());
    anchor_spl::token_interface::token_metadata_update_authority(
        a.metadata_authority_context().with_signer(seeds),
        new_authority,
    )?;
    Ok(())
}











#[derive(Accounts)]
pub struct InitBondingOnMeteora<'info> {
    #[account(mut)]
    pub admin: Signer<'info>,
    #[account(mut)]
    pub token_mint: Signer<'info>,
    pub funding_mint: Box<InterfaceAccount<'info, Mint>>,
    #[account(init, payer = admin, space = 256, seeds = [b"state", token_mint.key().as_ref()], bump)]
    pub state: Box<Account<'info, State>>,
    #[account(seeds = [b"fee_share_state", token_mint.key().as_ref()], bump, seeds::program = fee_share_trader_dao::ID,
        constraint = fee_authority.creator == admin.key() @ RecoveredError::InvalidFeeAuthority,
        constraint = fee_authority.funding_mint == funding_mint.key() @ RecoveredError::InvalidFeeAuthority,
        constraint = fee_authority.dao_mint == token_mint.key() @ RecoveredError::InvalidFeeAuthority)]
    pub fee_authority: Box<Account<'info, FeeShareState>>,
    #[account(address = DBC_CONFIG)]
    pub dbc_config: UncheckedAccount<'info>,
    /// CHECK: Created and validated by DBC.
    #[account(mut)]
    pub pool: UncheckedAccount<'info>,
    /// CHECK: DBC vault PDA.
    #[account(mut, seeds = [b"token_vault", token_mint.key().as_ref(), pool.key().as_ref()], bump, seeds::program = dbc_program.key())]
    pub pool_token_vault: UncheckedAccount<'info>,
    /// CHECK: DBC vault PDA.
    #[account(mut, seeds = [b"token_vault", funding_mint.key().as_ref(), pool.key().as_ref()], bump, seeds::program = dbc_program.key())]
    pub pool_funding_vault: UncheckedAccount<'info>,
    /// CHECK: Global creator and metadata authority PDA.
    #[account(mut, seeds = [b"meteora_authority"], bump)]
    pub meteora_authority: UncheckedAccount<'info>,
    /// CHECK: External authority PDA.
    #[account(seeds = [b"pool_authority"], bump, seeds::program = DBC_PROGRAM)]
    pub pool_authority: UncheckedAccount<'info>,
    /// CHECK: External event PDA.
    #[account(seeds = [b"__event_authority"], bump, seeds::program = DBC_PROGRAM)]
    pub dbc_event_authority: UncheckedAccount<'info>,
    pub funding_token_program: Interface<'info, TokenInterface>,
    pub token_program: Program<'info, anchor_spl::token_2022::Token2022>,
    pub associated_token_program: Program<'info, AssociatedToken>,
    pub system_program: Program<'info, System>,
    /// CHECK: External executable identity.
    pub dbc_program: Program<'info, DbcProgram>,
}


impl<'info> InitBondingOnMeteora<'info> {
    #[inline(never)]
    pub fn initialize_pool_context(&self) -> CpiContext<'_, '_, '_, 'info, dbc_cpi::InitializeVirtualPoolWithToken2022<'info>> {
        CpiContext::new(self.dbc_program.to_account_info(), dbc_cpi::InitializeVirtualPoolWithToken2022 {
            config: self.dbc_config.to_account_info(),
            pool_authority: self.pool_authority.to_account_info(),
            creator: self.meteora_authority.to_account_info(),
            base_mint: self.token_mint.to_account_info(),
            quote_mint: self.funding_mint.to_account_info(),
            pool: self.pool.to_account_info(),
            base_vault: self.pool_token_vault.to_account_info(),
            quote_vault: self.pool_funding_vault.to_account_info(),
            payer: self.admin.to_account_info(),
            token_quote_program: self.funding_token_program.to_account_info(),
            token_program: self.token_program.to_account_info(),
            system_program: self.system_program.to_account_info(),
            event_authority: self.dbc_event_authority.to_account_info(),
            program: self.dbc_program.to_account_info(),
        })
    }
    #[inline(never)]
    pub fn metadata_authority_context(&self) -> CpiContext<'_, '_, '_, 'info, anchor_spl::token_interface::TokenMetadataUpdateAuthority<'info>> {
        let cpi_program = self.dbc_program.to_account_info();
        let cpi_accounts = anchor_spl::token_interface::TokenMetadataUpdateAuthority {
            token_program_id: self.token_program.to_account_info(),
            metadata: self.token_mint.to_account_info(),
            current_authority: self.meteora_authority.to_account_info(),
            new_authority: self.state.to_account_info(),
        };
        CpiContext::new(cpi_program, cpi_accounts)
    }
}
