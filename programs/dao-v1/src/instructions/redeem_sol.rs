use crate::*;











pub fn handle_redeem_sol(ctx: Context<RedeemSol>, amount: u64) -> Result<()> {

    if ctx.accounts.user_sol_redeem.dao_burn_redeemed + amount > ctx.accounts.user_dao_burned.dao_burned {
        return Err(RecoveredError::Redeem_ExceedOwned.into());
    }
    ctx.accounts.user_sol_redeem.dao_burn_redeemed += amount;
    if ctx.accounts.sol_redeem.total_amount.is_none() {
        ctx.accounts.sol_redeem.total_amount = Some(ctx.accounts.wallet.lamports());
    }



    let payout =                 (ctx.accounts.sol_redeem.total_amount.unwrap() as u128 * amount as u128 / ctx.accounts.dao_mint.supply as u128) as u64;


    ctx.accounts.sol_redeem.total_distributed += payout;
    let cpi_accounts = anchor_lang::system_program::Transfer {
        from: ctx.accounts.wallet.to_account_info(),
        to: ctx.accounts.signer.to_account_info(),
    };
    let cpi_program = ctx.accounts.system_program.to_account_info();
    let mint = ctx.accounts.dao_mint.key();
    let signer_seeds: &[&[&[u8]]] = &[&[b"wallet", mint.as_ref(), &[ctx.bumps.wallet]]];
    let cpi_context = CpiContext::new(cpi_program, cpi_accounts).with_signer(signer_seeds);
    anchor_lang::system_program::transfer(cpi_context, payout)?;
    Ok(())
}




#[derive(Accounts)]
pub struct RedeemSol<'info> {
    #[account(mut)]
    pub signer: Signer<'info>,
    pub dao_mint: InterfaceAccount<'info, Mint>,
    /// CHECK: Only the derived treasury wallet can be debited.
    #[account(mut, seeds = [b"wallet", dao_mint.key().as_ref()], bump)]
    pub wallet: SystemAccount<'info>,
    #[account(mut, seeds = [b"user_metadata", dao_mint.key().as_ref(), signer.key().as_ref()], bump)]
    pub user_dao_burned: Account<'info, UserDaoBurned>,
    #[account(init_if_needed, payer = signer, space = 25,
        seeds = [b"sol_redeem", dao_mint.key().as_ref()], bump)]
    pub sol_redeem: Account<'info, TokenAccountRedemption>,
    #[account(init_if_needed, payer = signer, space = 16,
        seeds = [b"user_sol_redeem", dao_mint.key().as_ref(), signer.key().as_ref()], bump)]
    pub user_sol_redeem: Account<'info, UserDaoBurnRedeemed>,
    pub system_program: Program<'info, System>,
}

