use anchor_lang::prelude::*;

#[account]
pub struct FeeShareState {
    pub total_fees: u64,
    pub funding_mint: Pubkey,
    pub dao_mint: Pubkey,
    pub creator: Pubkey,
    pub referrer: Option<Pubkey>,
    pub creator_distributed: u64,
    pub referrer_distributed: u64,
    pub platform_distributed: u64,
}
