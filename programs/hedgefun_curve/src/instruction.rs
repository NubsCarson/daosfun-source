use anchor_lang::prelude::*;
#[derive(AnchorSerialize, AnchorDeserialize)]
pub struct MigrateLiquidity;

// Opaque wire payload; original field names and trade scalar types are not established.
#[derive(AnchorSerialize, AnchorDeserialize)]
pub struct BuyToken { pub data: [u8; 16] }

// Opaque wire payload; original field names and trade scalar types are not established.
#[derive(AnchorSerialize, AnchorDeserialize)]
pub struct SellToken { pub data: [u8; 16] }

// Opaque wire payload; original field names and trade scalar types are not established.
#[derive(AnchorSerialize, AnchorDeserialize)]
pub struct CollectFee { pub data: Option<[u8; 8]> }
