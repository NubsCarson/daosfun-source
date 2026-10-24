macro_rules! recovered_cpi { () => {
use anchor_lang::prelude::*;
pub mod accounts { pub use crate::__cpi_client_accounts_collect_fee::*; pub use crate::__cpi_client_accounts_sell_token::*; pub use crate::__cpi_client_accounts_buy_token::*; pub use crate::__cpi_client_accounts_migrate_liquidity::*; }
pub fn migrate_liquidity<'a, 'b, 'c, 'info>(ctx: CpiContext<'a, 'b, 'c, 'info, accounts::MigrateLiquidity<'info>>) -> Result<()> {
 let ix = {
  let ix = crate::instruction::MigrateLiquidity;
  let mut data = Vec::with_capacity(256);
  data.extend_from_slice(&[131, 168, 36, 158, 107, 147, 151, 163]);
  AnchorSerialize::serialize(&ix, &mut data).map_err(|_| anchor_lang::error::ErrorCode::InstructionDidNotSerialize)?;
  let accounts = ctx.to_account_metas(None);
  anchor_lang::solana_program::instruction::Instruction { program_id: ctx.program.key(), accounts, data }
 };
 let acc_infos = ctx.to_account_infos();
 anchor_lang::solana_program::program::invoke_signed(&ix, &acc_infos, ctx.signer_seeds).map_or_else(|e| Err(Into::into(e)), |_| { Ok(()) })
}


pub fn buy_token<'a, 'b, 'c, 'info>(ctx: CpiContext<'a, 'b, 'c, 'info, accounts::BuyToken<'info>>, data: [u8; 16]) -> Result<()> {
let ix = { let ix = crate::instruction::BuyToken { data }; let mut data = Vec::with_capacity(256);
data.extend_from_slice(&[138, 127, 14, 91, 38, 87, 115, 105]);
AnchorSerialize::serialize(&ix, &mut data).map_err(|_| anchor_lang::error::ErrorCode::InstructionDidNotSerialize)?;
let accounts = ctx.to_account_metas(None); anchor_lang::solana_program::instruction::Instruction {program_id: ctx.program.key(), accounts, data} };
let acc_infos=ctx.to_account_infos();
anchor_lang::solana_program::program::invoke_signed(&ix, &acc_infos, ctx.signer_seeds).map_or_else(|e| Err(Into::into(e)), |_| {Ok(())})
}

pub fn sell_token<'a, 'b, 'c, 'info>(ctx: CpiContext<'a, 'b, 'c, 'info, accounts::SellToken<'info>>, data: [u8; 16]) -> Result<()> {
let ix = { let ix = crate::instruction::SellToken { data }; let mut data = Vec::with_capacity(256);
data.extend_from_slice(&[109, 61, 40, 187, 230, 176, 135, 174]);
AnchorSerialize::serialize(&ix, &mut data).map_err(|_| anchor_lang::error::ErrorCode::InstructionDidNotSerialize)?;
let accounts = ctx.to_account_metas(None); anchor_lang::solana_program::instruction::Instruction {program_id: ctx.program.key(), accounts, data} };
let acc_infos=ctx.to_account_infos();
anchor_lang::solana_program::program::invoke_signed(&ix, &acc_infos, ctx.signer_seeds).map_or_else(|e| Err(Into::into(e)), |_| {Ok(())})
}

pub fn collect_fee<'a, 'b, 'c, 'info>(ctx: CpiContext<'a, 'b, 'c, 'info, accounts::CollectFee<'info>>, data: Option<[u8; 8]>) -> Result<()> {
let ix = { let ix = crate::instruction::CollectFee { data }; let mut data = Vec::with_capacity(256);
data.extend_from_slice(&[60, 173, 247, 103, 4, 93, 130, 48]);
AnchorSerialize::serialize(&ix, &mut data).map_err(|_| anchor_lang::error::ErrorCode::InstructionDidNotSerialize)?;
let accounts = ctx.to_account_metas(None); anchor_lang::solana_program::instruction::Instruction {program_id: ctx.program.key(), accounts, data} };
let acc_infos=ctx.to_account_infos();
anchor_lang::solana_program::program::invoke_signed(&ix, &acc_infos, ctx.signer_seeds).map_or_else(|e| Err(Into::into(e)), |_| {Ok(())})
}

}; }
recovered_cpi!();
