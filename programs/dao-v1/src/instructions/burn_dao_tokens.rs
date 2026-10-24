use crate::*;









pub fn handle_burn_dao_tokens(ctx: Context<BurnDaoTokens>, dao_mint_amount: u64) -> Result<()> {



    require!(ctx.accounts.state.redemption_started, RecoveredError::Redeem_NotStarted);
    if dao_mint_amount > 0 {
        let cpi_program = ctx.accounts.dao_token_program.to_account_info();
        let cpi_accounts = TransferChecked {
            from: ctx.accounts.dao_mint_signer_ata.to_account_info(),
            to: ctx.accounts.dao_mint_state_ata.to_account_info(),
            authority: ctx.accounts.signer.to_account_info(),
            mint: ctx.accounts.dao_mint.to_account_info(),
        };
        let cpi_context = CpiContext::new(cpi_program, cpi_accounts);
        token_interface::transfer_checked(
            cpi_context,
            dao_mint_amount,
            ctx.accounts.dao_mint.decimals,
        )?;

        ctx.accounts.user_dao_burned.dao_burned += dao_mint_amount;
    }
    Ok(())
}


#[derive(Accounts)]
pub struct BurnDaoTokens<'info> {
    #[account(mut)]
    pub signer: Signer<'info>,
    pub dao_mint: InterfaceAccount<'info, Mint>,
    #[account(mut, seeds = [b"state", dao_mint.key().as_ref()], bump, constraint = state.dao_mint == dao_mint.key())]
    pub state: Box<Account<'info, State>>,
    #[account(mut, associated_token::mint = dao_mint, associated_token::authority = signer,
        associated_token::token_program = dao_token_program)]
    pub dao_mint_signer_ata: InterfaceAccount<'info, TokenAccount>,
    #[account(mut, associated_token::mint = dao_mint, associated_token::authority = state,
        associated_token::token_program = dao_token_program)]
    pub dao_mint_state_ata: InterfaceAccount<'info, TokenAccount>,
    #[account(init_if_needed, payer = signer, space = 16,
        seeds = [b"user_metadata", dao_mint.key().as_ref(), signer.key().as_ref()], bump)]
    pub user_dao_burned: Account<'info, UserDaoBurned>,
    pub dao_token_program: Interface<'info, TokenInterface>,
    pub system_program: Program<'info, System>,
    pub associated_token_program: Program<'info, AssociatedToken>,
}

