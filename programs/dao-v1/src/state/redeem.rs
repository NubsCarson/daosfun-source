use anchor_lang::prelude::*;
// Preserve recovered account macro line numbers for exact-build experiments.
#[account]
pub struct UserDaoBurned {
    pub dao_burned: u64,
}


#[account]
pub struct TokenAccountRedemption {
    pub total_amount: Option<u64>,
    pub total_distributed: u64,
}





#[account]
pub struct UserDaoBurnRedeemed {
    pub dao_burn_redeemed: u64,
}
