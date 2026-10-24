use anchor_lang::prelude::*;
// Preserve recovered account macro line numbers for exact-build experiments.


#[account]
pub struct CosignState {
    /// Original field name is unknown; this byte selects the PDA namespace.
    pub id: u8,
    pub signer: Pubkey,
}
