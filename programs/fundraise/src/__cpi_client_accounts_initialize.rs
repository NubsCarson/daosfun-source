use anchor_lang::prelude::*;

pub struct Initialize<'info> {
    pub payer: AccountInfo<'info>,
    pub authority: AccountInfo<'info>,
    pub token_mint: AccountInfo<'info>,
    pub funding_mint: AccountInfo<'info>,
    pub state: AccountInfo<'info>,
    pub authority_token_vault: AccountInfo<'info>,
    pub token_vault: AccountInfo<'info>,
    pub recipient: AccountInfo<'info>,
    pub whitelist_authority: Option<AccountInfo<'info>>,
    pub token_program: AccountInfo<'info>,
    pub associated_token_program: AccountInfo<'info>,
    pub system_program: AccountInfo<'info>,
}
impl<'info> ToAccountMetas for Initialize<'info> {
    fn to_account_metas(&self, _is_signer: Option<bool>) -> Vec<anchor_lang::solana_program::instruction::AccountMeta> {
        let mut account_metas = vec![];
        account_metas.push(anchor_lang::solana_program::instruction::AccountMeta::new(anchor_lang::Key::key(&self.payer), true));
        account_metas.push(anchor_lang::solana_program::instruction::AccountMeta::new_readonly(anchor_lang::Key::key(&self.authority), true));
        account_metas.push(anchor_lang::solana_program::instruction::AccountMeta::new_readonly(anchor_lang::Key::key(&self.token_mint), false));
        account_metas.push(anchor_lang::solana_program::instruction::AccountMeta::new_readonly(anchor_lang::Key::key(&self.funding_mint), false));
        account_metas.push(anchor_lang::solana_program::instruction::AccountMeta::new(anchor_lang::Key::key(&self.state), false));
        account_metas.push(anchor_lang::solana_program::instruction::AccountMeta::new(anchor_lang::Key::key(&self.authority_token_vault), false));
        account_metas.push(anchor_lang::solana_program::instruction::AccountMeta::new(anchor_lang::Key::key(&self.token_vault), false));
        account_metas.push(anchor_lang::solana_program::instruction::AccountMeta::new_readonly(anchor_lang::Key::key(&self.recipient), false));
        if let Some(whitelist_authority) = &self.whitelist_authority { account_metas.push(anchor_lang::solana_program::instruction::AccountMeta::new_readonly(anchor_lang::Key::key(whitelist_authority), false)); } else { account_metas.push(anchor_lang::solana_program::instruction::AccountMeta::new_readonly(crate::ID, false)); }
        account_metas.push(anchor_lang::solana_program::instruction::AccountMeta::new_readonly(anchor_lang::Key::key(&self.token_program), false));
        account_metas.push(anchor_lang::solana_program::instruction::AccountMeta::new_readonly(anchor_lang::Key::key(&self.associated_token_program), false));
        account_metas.push(anchor_lang::solana_program::instruction::AccountMeta::new_readonly(anchor_lang::Key::key(&self.system_program), false));
        account_metas
    }
}
impl<'info> ToAccountInfos<'info> for Initialize<'info> {
    fn to_account_infos(&self) -> Vec<AccountInfo<'info>> {
        let mut account_infos = vec![];
        account_infos.extend(anchor_lang::ToAccountInfos::to_account_infos(&self.payer));
        account_infos.extend(anchor_lang::ToAccountInfos::to_account_infos(&self.authority));
        account_infos.extend(anchor_lang::ToAccountInfos::to_account_infos(&self.token_mint));
        account_infos.extend(anchor_lang::ToAccountInfos::to_account_infos(&self.funding_mint));
        account_infos.extend(anchor_lang::ToAccountInfos::to_account_infos(&self.state));
        account_infos.extend(anchor_lang::ToAccountInfos::to_account_infos(&self.authority_token_vault));
        account_infos.extend(anchor_lang::ToAccountInfos::to_account_infos(&self.token_vault));
        account_infos.extend(anchor_lang::ToAccountInfos::to_account_infos(&self.recipient));
        account_infos.extend(anchor_lang::ToAccountInfos::to_account_infos(&self.whitelist_authority));
        account_infos.extend(anchor_lang::ToAccountInfos::to_account_infos(&self.token_program));
        account_infos.extend(anchor_lang::ToAccountInfos::to_account_infos(&self.associated_token_program));
        account_infos.extend(anchor_lang::ToAccountInfos::to_account_infos(&self.system_program));
        account_infos
    }
}
