use crate::*;
#[inline(never)]
pub fn finalize(ctx: Context<FinalizeMeteoraBonding>) -> Result<()> {
    let seeds: &[&[&[u8]]] = &[&[b"meteora_authority", &[ctx.bumps.meteora_authority]]];
    let a = ctx.accounts;
    dbc_cpi::cpi::withdraw_migration_fee(a.withdraw_migration_fee_context().with_signer(seeds), 0)?;
    let config = a.dbc_config.load()?;
    a.state.funding_goal = config.migration_quote_threshold;
    a.state.curve_initialized = true;
    Ok(())
}
impl<'info> FinalizeMeteoraBonding<'info> {
    #[inline(never)]
    pub fn withdraw_migration_fee_context(&self) -> CpiContext<'_, '_, '_, 'info, dbc_cpi::WithdrawMigrationFee<'info>> {
        CpiContext::new(self.dbc_program.to_account_info(), dbc_cpi::WithdrawMigrationFee {
            config: self.dbc_config.to_account_info(),
            virtual_pool: self.pool.to_account_info(),
            pool_authority: self.pool_authority.to_account_info(),
            quote_mint: self.funding_mint.to_account_info(),
            quote_vault: self.pool_funding_vault.to_account_info(),
            token_quote_program: self.funding_token_program.to_account_info(),
            token_quote_account: self.wallet_funding_ata.to_account_info(),
            sender: self.meteora_authority.to_account_info(),
            event_authority: self.dbc_event_authority.to_account_info(),
            program: self.dbc_program.to_account_info(),
        })
    }
}

#[derive(Accounts)]
pub struct FinalizeMeteoraBonding<'info> {
    #[account(mut)]
    pub signer: Signer<'info>,
    pub token_mint: Box<InterfaceAccount<'info, Mint>>,
    pub funding_mint: Box<InterfaceAccount<'info, Mint>>,
    #[account(mut, seeds = [b"state", token_mint.key().as_ref()], bump,
        constraint = state.dao_mint == token_mint.key() && state.funding_mint == funding_mint.key() @ RecoveredError::Unauthorized,
        constraint = state.curve_initialized == false @ RecoveredError::InitCurve_AlreadyInitialized)]
    pub state: Box<Account<'info, State>>,
    /// CHECK: Treasury PDA.
    #[account(seeds = [b"wallet", token_mint.key().as_ref()], bump)]
    pub wallet: SystemAccount<'info>,
    #[account(mut, associated_token::mint = funding_mint, associated_token::authority = wallet, associated_token::token_program = funding_token_program)]
    pub wallet_funding_ata: Box<InterfaceAccount<'info, TokenAccount>>,
    #[account(address = DBC_CONFIG)]
    pub dbc_config: AccountLoader<'info, ExternalDbcConfig>,
    /// CHECK: DBC validates the pool.
    #[account(mut)]
    pub pool: UncheckedAccount<'info>,
    /// CHECK: External token-vault PDA.
    #[account(mut, seeds = [b"token_vault", funding_mint.key().as_ref(), pool.key().as_ref()], bump, seeds::program = dbc_program.key())]
    pub pool_funding_vault: UncheckedAccount<'info>,
    /// CHECK: External token-vault PDA.
    #[account(mut, seeds = [b"token_vault", token_mint.key().as_ref(), pool.key().as_ref()], bump, seeds::program = dbc_program.key())]
    pub pool_token_vault: UncheckedAccount<'info>,
    /// CHECK: Global signing PDA.
    #[account(seeds = [b"meteora_authority"], bump)]
    pub meteora_authority: UncheckedAccount<'info>,
    /// CHECK: External authority PDA.
    #[account(seeds = [b"pool_authority"], bump, seeds::program = DBC_PROGRAM)]
    pub pool_authority: UncheckedAccount<'info>,
    /// CHECK: External event PDA.
    #[account(seeds = [b"__event_authority"], bump, seeds::program = DBC_PROGRAM)]
    pub dbc_event_authority: UncheckedAccount<'info>,
    pub token_program: Interface<'info, TokenInterface>,
    pub funding_token_program: Interface<'info, TokenInterface>,
    pub associated_token_program: Program<'info, AssociatedToken>,
    /// CHECK: External executable identity.
    pub dbc_program: Program<'info, DbcProgram>,
}
