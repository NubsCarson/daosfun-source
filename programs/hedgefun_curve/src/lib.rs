use anchor_lang::prelude::*;
pub mod state;
declare_id!("HedgENAip7ZEzRj6T3ZbY1PmDFXU5XKx1BFSKbxvVD7V");

pub mod instruction;
pub mod cpi;
mod __cpi_client_accounts_migrate_liquidity;

pub mod program {
    #[derive(Clone)]
    pub struct HedgefunCurve;
    impl anchor_lang::Id for HedgefunCurve {
        fn id() -> anchor_lang::prelude::Pubkey { crate::ID }
    }
}

pub mod migrate_liquidity;

mod __cpi_client_accounts_buy_token;

mod __cpi_client_accounts_sell_token;

mod __cpi_client_accounts_collect_fee;
