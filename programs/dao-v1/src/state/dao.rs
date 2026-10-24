use anchor_lang::prelude::*;
// Preserve recovered account macro line numbers for exact-build experiments.





































































































#[account]
pub struct State {
    pub admin: Pubkey,
    pub dao_mint: Pubkey,
    pub funding_mint: Pubkey,
    pub funding_goal: u64,
    pub admin_closed_fund: bool,
    pub redemption_started: bool,
    pub expiration_timestamp: i64,
    pub delegate_authorities: [Option<Pubkey>; 3],
    pub carry_basis: u16,
    pub fee_authority: Pubkey,
    pub curve_initialized: bool,
}
