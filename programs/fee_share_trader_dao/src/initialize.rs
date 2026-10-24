use anchor_lang::prelude::*;
use anchor_spl::token_interface::Mint;
use crate::state::FeeShareState;

#[derive(Accounts)]
pub struct Initialize<'info> {
 #[account(mut)]
 pub payer: Signer<'info>,
 pub dao_mint: Signer<'info>,
 pub funding_mint: InterfaceAccount<'info, Mint>,
 #[account(init, payer = payer, space = 169, seeds = [b"fee_share_state", dao_mint.key().as_ref()], bump)]
 pub fee_share_state: Account<'info, FeeShareState>,
 pub system_program: Program<'info, System>,
}

pub fn handle_initialize(ctx: Context<Initialize>, creator: Pubkey, referrer: Option<Pubkey>) -> Result<()> {
 ctx.accounts.fee_share_state.funding_mint = ctx.accounts.funding_mint.key();
 ctx.accounts.fee_share_state.dao_mint = ctx.accounts.dao_mint.key();
 ctx.accounts.fee_share_state.creator = creator;
 ctx.accounts.fee_share_state.referrer = referrer;
 Ok(())
}
