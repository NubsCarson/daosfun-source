use anchor_lang::prelude::*;
use anchor_spl::token_interface::Mint;
use crate::state::fundraise::FundraiseState;

#[derive(Accounts)]
pub struct MakePublic<'info> {
    pub signer: Signer<'info>,
    pub token_mint: InterfaceAccount<'info, Mint>,
    #[account(mut,
        seeds = [b"fundraise", state.admin.as_ref(), token_mint.key().as_ref()],
        bump,
        constraint = state.token_mint == token_mint.key() @ MakePublicError::InvalidTokenMint,
        constraint = state.whitelist_authority.unwrap() == signer.key() @ MakePublicError::Unauthorized
    )]
    pub state: Account<'info, FundraiseState>,
}

pub fn handle_make_public(ctx: Context<MakePublic>) -> Result<()> {
    require!(Clock::get()?.unix_timestamp < ctx.accounts.state.expiration, MakePublicError::Expired);
    ctx.accounts.state.trailing_flag = true;
    Ok(())
}

#[error_code]
pub enum MakePublicError {
    #[msg("Invalid token mint")]
    InvalidTokenMint = 0,
    #[msg("Expired")]
    Expired = 4,
    #[msg("Unauthorized")]
    Unauthorized = 5,
}
