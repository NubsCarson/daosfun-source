use crate::*;






















#[inline(never)]
pub fn claim(ctx: Context<ClaimDbcTradingFees>) -> Result<()> {
    let seeds: &[&[&[u8]]] = &[&[b"meteora_authority", &[ctx.bumps.meteora_authority]]];
    let a = ctx.accounts;
    let before_token = a.meteora_authority_token_ata.amount;
    let before_funding = a.meteora_authority_funding_ata.amount;
    dbc_cpi::cpi::claim_trading_fee(a.claim_trading_fee_context().with_signer(seeds), u64::MAX, u64::MAX)?;
    a.meteora_authority_funding_ata.reload()?;
    a.meteora_authority_token_ata.reload()?;
    let after_token = a.meteora_authority_token_ata.amount;
    let after_funding = a.meteora_authority_funding_ata.amount;


    token_interface::transfer_checked(
        a.transfer_claim_token_context().with_signer(seeds),
        after_token - before_token,
        a.token_mint.decimals,
    )?;


    token_interface::transfer_checked(
        a.transfer_claim_funding_context().with_signer(seeds),
        after_funding - before_funding,
        a.funding_mint.decimals,
    )?;
    Ok(())
}

impl<'info> ClaimDbcTradingFees<'info> {
    #[inline(never)]
    pub fn claim_trading_fee_context(&self) -> CpiContext<'_, '_, '_, 'info, dbc_cpi::ClaimTradingFee<'info>> {
        CpiContext::new(self.dbc_program.to_account_info(), dbc_cpi::ClaimTradingFee {
            config: self.dbc_config.to_account_info(),
            pool: self.pool.to_account_info(),
            token_a_account: self.meteora_authority_token_ata.to_account_info(),
            token_b_account: self.meteora_authority_funding_ata.to_account_info(),
            pool_authority: self.pool_authority.to_account_info(),
            quote_mint: self.funding_mint.to_account_info(),
            fee_claimer: self.meteora_authority.to_account_info(),
            quote_vault: self.pool_funding_vault.to_account_info(),
            token_quote_program: self.funding_token_program.to_account_info(),
            event_authority: self.dbc_event_authority.to_account_info(),
            program: self.dbc_program.to_account_info(),
            base_vault: self.pool_token_vault.to_account_info(),
            base_mint: self.token_mint.to_account_info(),
            token_base_program: self.token_program.to_account_info(),
        })
    }
}
impl<'info> ClaimDbcTradingFees<'info> {
    #[inline(never)]
    pub fn transfer_claim_token_context(&self) -> CpiContext<'_, '_, '_, 'info, TransferChecked<'info>> {
        let cpi_program = self.token_program.to_account_info();
        let cpi_accounts = TransferChecked {
            from: self.meteora_authority_token_ata.to_account_info(),
            to: self.fee_authority_token_ata.to_account_info(),
            authority: self.meteora_authority.to_account_info(),
            mint: self.token_mint.to_account_info(),
        };
        CpiContext::new(cpi_program, cpi_accounts)
    }
}
impl<'info> ClaimDbcTradingFees<'info> {
    #[inline(never)]
    pub fn transfer_claim_funding_context(&self) -> CpiContext<'_, '_, '_, 'info, TransferChecked<'info>> {
        let cpi_program = self.funding_token_program.to_account_info();
        let cpi_accounts = TransferChecked {
            from: self.meteora_authority_funding_ata.to_account_info(),
            to: self.fee_authority_funding_ata.to_account_info(),
            authority: self.meteora_authority.to_account_info(),
            mint: self.funding_mint.to_account_info(),
        };
        CpiContext::new(cpi_program, cpi_accounts)
    }
}

#[derive(Accounts)]
pub struct ClaimDbcTradingFees<'info> {
    #[account(signer, seeds = [b"fee_share_state", token_mint.key().as_ref()], bump, seeds::program = fee_share_trader_dao::ID,
        constraint = funding_mint.key() == fee_authority.funding_mint && token_mint.key() == fee_authority.dao_mint)]
    pub fee_authority: Box<Account<'info, FeeShareState>>,
    pub token_mint: Box<InterfaceAccount<'info, Mint>>,
    pub funding_mint: Box<InterfaceAccount<'info, Mint>>,
    #[account(address = DBC_CONFIG)]
    pub dbc_config: AccountLoader<'info, ExternalDbcConfig>,
    /// CHECK: Validated by the external DBC program.
    #[account(mut)]
    pub pool: UncheckedAccount<'info>,
    /// CHECK: PDA validated here; token data is validated by DBC.
    #[account(mut, seeds = [b"token_vault", funding_mint.key().as_ref(), pool.key().as_ref()], bump, seeds::program = dbc_program.key())]
    pub pool_funding_vault: UncheckedAccount<'info>,
    /// CHECK: PDA validated here; token data is validated by DBC.
    #[account(mut, seeds = [b"token_vault", token_mint.key().as_ref(), pool.key().as_ref()], bump, seeds::program = dbc_program.key())]
    pub pool_token_vault: UncheckedAccount<'info>,
    /// CHECK: Global authority PDA signs CPI calls.
    #[account(seeds = [b"meteora_authority"], bump)]
    pub meteora_authority: UncheckedAccount<'info>,
    #[account(mut, associated_token::mint = funding_mint, associated_token::authority = meteora_authority, associated_token::token_program = funding_token_program)]
    pub meteora_authority_funding_ata: Box<InterfaceAccount<'info, TokenAccount>>,
    #[account(mut, associated_token::mint = token_mint, associated_token::authority = meteora_authority, associated_token::token_program = token_program)]
    pub meteora_authority_token_ata: Box<InterfaceAccount<'info, TokenAccount>>,
    #[account(mut, associated_token::mint = funding_mint, associated_token::authority = fee_authority, associated_token::token_program = funding_token_program)]
    pub fee_authority_funding_ata: Box<InterfaceAccount<'info, TokenAccount>>,
    #[account(mut, associated_token::mint = token_mint, associated_token::authority = fee_authority, associated_token::token_program = token_program)]
    pub fee_authority_token_ata: Box<InterfaceAccount<'info, TokenAccount>>,
    /// CHECK: External global PDA.
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
