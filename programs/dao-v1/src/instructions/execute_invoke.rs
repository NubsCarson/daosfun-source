use crate::*;






#[inline(never)]
pub fn handle_execute_invoke<'info>(ctx: Context<'_, '_, '_, 'info, ExecuteInvoke<'info>>, instruction_data: Vec<u8>) -> Result<()> {
    let state = &ctx.accounts.state;
    require!(!state.admin_closed_fund, RecoveredError::Execute_FundClosed);




    require!(state.delegate_authorities.contains(&Some(ctx.accounts.authority.key())) || state.admin == ctx.accounts.authority.key(), RecoveredError::Unauthorized);
    let metas = ctx.remaining_accounts.iter().map(|account| anchor_lang::solana_program::instruction::AccountMeta {
        pubkey: account.key(),
        is_signer: account.key() == ctx.accounts.wallet.key() || account.is_signer,
        is_writable: account.is_writable,
    }).collect();
    let infos: Vec<AccountInfo<'info>> = ctx.remaining_accounts.iter().map(|account| {
        let mut info = account.clone();
        if info.key() == ctx.accounts.wallet.key() { info.is_signer = true; }
        info
    }).collect();
    let instruction = anchor_lang::solana_program::instruction::Instruction {
        program_id: ctx.accounts.instruction_program.key(), accounts: metas, data: instruction_data,
    };
    let mint = ctx.accounts.dao_mint.key();
    let signer_seeds: &[&[&[u8]]] = &[&[b"wallet", mint.as_ref(), &[ctx.bumps.wallet]]];
    anchor_lang::solana_program::program::invoke_signed(&instruction, &infos, signer_seeds)?;
    Ok(())
}

#[derive(Accounts)]
pub struct ExecuteInvoke<'info> {
    #[account(mut)]
    pub authority: Signer<'info>,
    pub dao_mint: InterfaceAccount<'info, Mint>,
    #[account(mut, seeds = [b"state", dao_mint.key().as_ref()], bump, constraint = state.dao_mint == dao_mint.key() @ RecoveredError::Unauthorized)]
    pub state: Account<'info, State>,
    /// CHECK: PDA identity is checked; the wallet is the signer passed to the CPI.
    #[account(mut, seeds = [b"wallet", dao_mint.key().as_ref()], bump)]
    pub wallet: SystemAccount<'info>,
    /// CHECK: The runtime validates the target when the CPI executes.
    pub instruction_program: UncheckedAccount<'info>,
    pub cosigner: Signer<'info>,
    #[account(seeds = [b"cosigner".as_ref(), &0u8.to_le_bytes()], bump,
        constraint = cosigner.key() == cosign_state.signer @ RecoveredError::Unauthorized)]
    pub cosign_state: Account<'info, CosignState>,
}
