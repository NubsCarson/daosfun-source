use anchor_lang::prelude::*;

#[account]
pub struct HedgefunCurve {
    pub initial_token_amount: u64,
    pub token_amount: u64,
    pub virtual_token_amount: u64,
    pub funding_amount: u64,
    pub virtual_funding_amount: u64,
    pub token_mint: Pubkey,
    pub funding_mint: Pubkey,
    pub complete: bool,
    pub completed_at: i64,
    pub migrated: bool,
    pub migrated_at: i64,
    pub opaque_tail_word: u64,
    pub opaque_tail_words: [u64; 4],
}
