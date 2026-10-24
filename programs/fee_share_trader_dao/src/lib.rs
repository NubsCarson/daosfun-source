use anchor_lang::prelude::*;
pub mod state;
declare_id!("Fee33nMZNbbC7Zm6Yx7tiHa9KH2Ao8fWTH3HNMkLMzWk");
pub mod initialize;
pub mod change_creator;
pub use initialize::*;
pub use change_creator::*;
pub mod init_with_legacy;
pub use init_with_legacy::*;
#[program]
pub mod fee_share_trader_dao {
 use super::*;
 pub fn init_with_legacy(ctx: Context<InitWithLegacy>) -> Result<()> { crate::init_with_legacy::handle_init_with_legacy(ctx) }
 pub fn initialize(ctx: Context<Initialize>, creator: Pubkey, referrer: Option<Pubkey>) -> Result<()> {
  crate::initialize::handle_initialize(ctx, creator, referrer)
 }
 pub fn change_creator(ctx: Context<ChangeCreator>) -> Result<()> {
  crate::change_creator::handle_change_creator(ctx)
 }
}
