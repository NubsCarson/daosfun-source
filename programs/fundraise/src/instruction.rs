use anchor_lang::prelude::*;
#[derive(AnchorSerialize, AnchorDeserialize)]
pub struct Initialize { pub token_amount: u64, pub funding_goal: u64, pub funding_duration: u32 }
#[derive(AnchorSerialize, AnchorDeserialize)]
pub struct CommitFunds { pub amount: u64 }
