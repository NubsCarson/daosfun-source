macro_rules! recovered_cpi { () => {
use anchor_lang::prelude::*;
use crate::instruction;
pub mod accounts {
    pub use crate::__cpi_client_accounts_initialize::*;
    pub use crate::__cpi_client_accounts_commit_funds::*;
}
pub fn initialize<'a, 'b, 'c, 'info>(ctx: CpiContext<'a, 'b, 'c, 'info, accounts::Initialize<'info>>, token_amount: u64, funding_goal: u64, funding_duration: u32) -> Result<()> {
    let ix = {
        let ix = instruction::Initialize { token_amount, funding_goal, funding_duration };
        let mut data = Vec::with_capacity(256);
        data.extend_from_slice(&[175, 175, 109, 31, 13, 152, 155, 237]);
        AnchorSerialize::serialize(&ix, &mut data).map_err(|_| anchor_lang::error::ErrorCode::InstructionDidNotSerialize)?;
        let accounts = ctx.to_account_metas(None);
        anchor_lang::solana_program::instruction::Instruction { program_id: ctx.program.key(), accounts, data }
    };
    let acc_infos = ctx.to_account_infos();
    anchor_lang::solana_program::program::invoke_signed(&ix, &acc_infos, ctx.signer_seeds)
        .map_or_else(|e| Err(Into::into(e)), |_| { Ok(()) })
}
pub fn commit_funds<'a, 'b, 'c, 'info>(ctx: CpiContext<'a, 'b, 'c, 'info, accounts::CommitFunds<'info>>, amount: u64) -> Result<()> {
    let ix = {
        let ix = instruction::CommitFunds { amount };
        let mut data = Vec::with_capacity(256);
        data.extend_from_slice(&[242, 226, 172, 204, 143, 241, 207, 248]);
        AnchorSerialize::serialize(&ix, &mut data).map_err(|_| anchor_lang::error::ErrorCode::InstructionDidNotSerialize)?;
        let accounts = ctx.to_account_metas(None);
        anchor_lang::solana_program::instruction::Instruction { program_id: ctx.program.key(), accounts, data }
    };
    let acc_infos = ctx.to_account_infos();
    anchor_lang::solana_program::program::invoke_signed(&ix, &acc_infos, ctx.signer_seeds)
        .map_or_else(|e| Err(Into::into(e)), |_| { Ok(()) })
}

}; }
recovered_cpi!();
