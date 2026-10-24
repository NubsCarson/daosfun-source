use crate::*;

#[inline(never)]
pub fn revoke_delegate_authority(ctx: Context<DelegateAuthority>, authority: Pubkey) -> Result<()> {
    for i in 0..ctx.accounts.state.delegate_authorities.len() {
        if ctx.accounts.state.delegate_authorities[i] == Some(authority) { ctx.accounts.state.delegate_authorities[i] = None; return Ok(()); }
    }
    Err(RecoveredError::Delegate_AuthorityNotFound.into())
}
