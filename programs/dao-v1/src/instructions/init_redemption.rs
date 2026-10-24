use crate::*;










#[inline(never)]
pub fn handle_init_redemption(ctx: Context<InitRedemption>) -> Result<()> {

    require!(ctx.accounts.state.redemption_started == false, RecoveredError::Redeem_AlreadyStarted);




    require!(ctx.accounts.state.admin_closed_fund, RecoveredError::Redeem_FundNotExpired);
    let mut carry = 0u64;
    if ctx.accounts.wallet_funding_ata.amount > ctx.accounts.state.funding_goal {
        carry = (ctx.accounts.state.carry_basis as u128 * (ctx.accounts.wallet_funding_ata.amount - ctx.accounts.state.funding_goal) as u128 / 10_000) as u64;
    }
    match carry {
        0 => {}
        _ => {
        let result = {
        let mint = ctx.accounts.dao_mint.key();
        let signer_seeds: &[&[&[u8]]] = &[&[b"wallet", mint.as_ref(), &[ctx.bumps.wallet]]];
        let cpi_program = ctx.accounts.token_program.to_account_info();
        let cpi_accounts = TransferChecked {
            from: ctx.accounts.wallet_funding_ata.to_account_info(), to: ctx.accounts.admin_funding_ata.to_account_info(),
            authority: ctx.accounts.wallet.to_account_info(), mint: ctx.accounts.funding_mint.to_account_info(),
        };
        let cpi_context = CpiContext::new(cpi_program, cpi_accounts).with_signer(signer_seeds);
        token_interface::transfer_checked(cpi_context, carry, ctx.accounts.funding_mint.decimals) };
        if result.is_err() { return result; }
        } }
    ctx.accounts.state.redemption_started = true;
    Ok(())
}

#[derive(Accounts)]
pub struct InitRedemption<'info> {
    #[account(mut)]
    pub signer: Signer<'info>,
    pub dao_mint: InterfaceAccount<'info, Mint>,
    pub funding_mint: InterfaceAccount<'info, Mint>,
    /// CHECK: The treasury identity is enforced by its PDA seeds.
    #[account(mut, seeds = [b"wallet", dao_mint.key().as_ref()], bump)]
    pub wallet: SystemAccount<'info>,
    #[account(mut, associated_token::mint = funding_mint, associated_token::authority = wallet,
        associated_token::token_program = token_program)]
    pub wallet_funding_ata: InterfaceAccount<'info, TokenAccount>,
    #[account(mut, associated_token::mint = funding_mint, associated_token::authority = state.admin,
        associated_token::token_program = token_program)]
    pub admin_funding_ata: InterfaceAccount<'info, TokenAccount>,
    #[account(mut, seeds = [b"state", dao_mint.key().as_ref()], bump,
        constraint = state.dao_mint == dao_mint.key(), constraint = state.funding_mint == funding_mint.key(),
        constraint = state.curve_initialized @ RecoveredError::UnexpectedState)]
    pub state: Account<'info, State>,
    pub token_program: Program<'info, anchor_spl::token::Token>,
    pub associated_token_program: Program<'info, AssociatedToken>,
}

