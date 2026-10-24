use anchor_lang::prelude::*;

#[account]
pub struct FundraiseState {
    pub admin: Pubkey,
    pub token_mint: Pubkey,
    pub funding_mint: Pubkey,
    pub token_deposit: u64,
    pub funding_goal: u64,
    pub expiration: i64,
    pub funding_received: u64,
    pub is_funded: bool,
    pub is_finalized: bool,
    pub recipient: Pubkey,
    pub whitelist_authority: Option<Pubkey>,
    pub trailing_flag: bool,
}
