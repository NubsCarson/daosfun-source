//! Recovered client-side instruction data; account execution stays in the deployed program.
use anchor_lang::prelude::*;

/// Wire layout verified against the deployed initialize argument decoder.
#[derive(AnchorSerialize, AnchorDeserialize)]
pub struct Initialize {
    pub creator: Pubkey,
    pub referrer: Option<Pubkey>,
}

impl Initialize {
    /// Decode arguments after the eight-byte Anchor instruction discriminator.
    pub fn decode(data: &mut &[u8]) -> std::io::Result<Self> {
        <Self as AnchorDeserialize>::deserialize(data)
    }
}
