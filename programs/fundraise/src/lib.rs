use anchor_lang::prelude::*;
pub mod state;
declare_id!("ETK5PUmiqVDRsd1TPFqCu84bsrLNG4YySZND96PEjW97");

pub mod program {
    #[derive(Clone)]
    pub struct Fundraise;
    impl anchor_lang::Id for Fundraise {
        fn id() -> anchor_lang::prelude::Pubkey { crate::ID }
    }
}

pub mod instruction;
pub mod cpi;
mod __cpi_client_accounts_initialize;
mod __cpi_client_accounts_commit_funds;

pub mod make_public;
