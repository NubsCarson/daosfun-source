use crate::*;

#[inline(never)]
pub fn add_delegate_authority(ctx: Context<DelegateAuthority>, authority: Pubkey) -> Result<()> {
    let mut added = false;
    for entry in ctx.accounts.state.delegate_authorities.iter_mut() {
        if *entry == Some(authority) { return Err(RecoveredError::Delegate_DuplicateAuthority.into()); }
        if entry.is_none() && !added { *entry = Some(authority); added = true; }
    }
    if !added { return Err(RecoveredError::Delegate_ExceededMax.into()); }
    Ok(())
}

#[derive(Accounts)]
pub struct DelegateAuthority<'info> {
    #[account(mut)]
    pub signer: Signer<'info>,
    pub dao_mint: InterfaceAccount<'info, Mint>,
    #[account(mut, seeds = [b"state", dao_mint.key().as_ref()], bump, constraint = state.dao_mint == dao_mint.key(), constraint = state.admin == signer.key() @ RecoveredError::Unauthorized)]
    pub state: Account<'info, State>,
}
