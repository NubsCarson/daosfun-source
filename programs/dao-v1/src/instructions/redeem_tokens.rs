use crate::*;














#[inline(never)]
pub fn handle_redeem_tokens(ctx: Context<RedeemTokens>, amount: u64) -> Result<()> {

    if ctx.accounts.user_dao_burn_redeemed.dao_burn_redeemed + amount > ctx.accounts.user_dao_burned.dao_burned {
        return Err(RecoveredError::Redeem_ExceedOwned.into());
    }
    ctx.accounts.user_dao_burn_redeemed.dao_burn_redeemed += amount;
    if ctx.accounts.token_account_redemption.total_amount.is_none() {
        ctx.accounts.token_account_redemption.total_amount = Some(ctx.accounts.redeem_wallet_token_acc.amount);
    }




    let payout =                 (ctx.accounts.token_account_redemption.total_amount.unwrap() as u128 * amount as u128 / ctx.accounts.dao_mint.supply as u128) as u64;


    ctx.accounts.token_account_redemption.total_distributed += payout;
    let mint = ctx.accounts.dao_mint.key();
    let signer_seeds: &[&[&[u8]]] = &[&[b"wallet", mint.as_ref(), &[ctx.bumps.wallet]]];
    let cpi_program = ctx.accounts.redeem_token_program.to_account_info();
    let cpi_accounts = TransferChecked {
        from: ctx.accounts.redeem_wallet_token_acc.to_account_info(),
        to: ctx.accounts.redeem_signer_ata.to_account_info(),
        authority: ctx.accounts.wallet.to_account_info(),
        mint: ctx.accounts.redeem_mint.to_account_info(),
    };
    let cpi_context = CpiContext::new(cpi_program, cpi_accounts).with_signer(signer_seeds);
    token_interface::transfer_checked(cpi_context, payout, ctx.accounts.redeem_mint.decimals)?;
    Ok(())
}









#[derive(Accounts)]
pub struct RedeemTokens<'info> {
    #[account(mut)]
    pub signer: Signer<'info>,
    pub dao_mint: InterfaceAccount<'info, Mint>,
    #[account(constraint = redeem_mint.key() != dao_mint.key())]
    pub redeem_mint: InterfaceAccount<'info, Mint>,
    /// CHECK: The treasury identity is enforced by its PDA seeds.
    #[account(mut, seeds = [b"wallet", dao_mint.key().as_ref()], bump)]
    pub wallet: SystemAccount<'info>,
    #[account(mut, token::mint = redeem_mint, token::authority = wallet,
        token::token_program = redeem_token_program)]
    pub redeem_wallet_token_acc: InterfaceAccount<'info, TokenAccount>,
    #[account(mut, associated_token::mint = redeem_mint,
        associated_token::authority = signer, associated_token::token_program = redeem_token_program)]
    pub redeem_signer_ata: InterfaceAccount<'info, TokenAccount>,
    #[account(mut, seeds = [b"user_metadata", dao_mint.key().as_ref(), signer.key().as_ref()], bump)]
    pub user_dao_burned: Account<'info, UserDaoBurned>,
    #[account(init_if_needed, payer = signer, space = 25,
        seeds = [b"token_acc_metadata", dao_mint.key().as_ref(), redeem_wallet_token_acc.key().as_ref()], bump)]
    pub token_account_redemption: Account<'info, TokenAccountRedemption>,
    #[account(init_if_needed, payer = signer, space = 16,
        seeds = [b"token_redeem", dao_mint.key().as_ref(), redeem_wallet_token_acc.key().as_ref(), signer.key().as_ref()], bump)]
    pub user_dao_burn_redeemed: Account<'info, UserDaoBurnRedeemed>,
    pub redeem_token_program: Interface<'info, TokenInterface>,
    pub system_program: Program<'info, System>,
    pub associated_token_program: Program<'info, AssociatedToken>,
}

