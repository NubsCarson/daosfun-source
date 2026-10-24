use anchor_lang::prelude::*;
pub struct MigrateLiquidity<'info> {
 pub payer: AccountInfo<'info>,
 pub authority: AccountInfo<'info>,
 pub token_mint: AccountInfo<'info>,
 pub funding_mint: AccountInfo<'info>,
 pub curve: AccountInfo<'info>,
 pub payer_funding_ata: AccountInfo<'info>,
 pub curve_funding_vault: AccountInfo<'info>,
 pub funding_token_program: AccountInfo<'info>,
 pub associated_token_program: AccountInfo<'info>,
}
impl<'info> ToAccountMetas for MigrateLiquidity<'info> {
 fn to_account_metas(&self, _is_signer: Option<bool>) -> Vec<anchor_lang::solana_program::instruction::AccountMeta> {
 let mut account_metas = vec![];
 account_metas.push(anchor_lang::solana_program::instruction::AccountMeta::new_readonly(anchor_lang::Key::key(&self.payer), true));
 account_metas.push(anchor_lang::solana_program::instruction::AccountMeta::new_readonly(anchor_lang::Key::key(&self.authority), true));
 account_metas.push(anchor_lang::solana_program::instruction::AccountMeta::new_readonly(anchor_lang::Key::key(&self.token_mint), false));
 account_metas.push(anchor_lang::solana_program::instruction::AccountMeta::new_readonly(anchor_lang::Key::key(&self.funding_mint), false));
 account_metas.push(anchor_lang::solana_program::instruction::AccountMeta::new(anchor_lang::Key::key(&self.curve), false));
 account_metas.push(anchor_lang::solana_program::instruction::AccountMeta::new(anchor_lang::Key::key(&self.payer_funding_ata), false));
 account_metas.push(anchor_lang::solana_program::instruction::AccountMeta::new(anchor_lang::Key::key(&self.curve_funding_vault), false));
 account_metas.push(anchor_lang::solana_program::instruction::AccountMeta::new_readonly(anchor_lang::Key::key(&self.funding_token_program), false));
 account_metas.push(anchor_lang::solana_program::instruction::AccountMeta::new_readonly(anchor_lang::Key::key(&self.associated_token_program), false));
 account_metas
 }
}
impl<'info> ToAccountInfos<'info> for MigrateLiquidity<'info> {
 fn to_account_infos(&self) -> Vec<AccountInfo<'info>> {
 let mut account_infos = vec![];
 account_infos.extend(anchor_lang::ToAccountInfos::to_account_infos(&self.payer));
 account_infos.extend(anchor_lang::ToAccountInfos::to_account_infos(&self.authority));
 account_infos.extend(anchor_lang::ToAccountInfos::to_account_infos(&self.token_mint));
 account_infos.extend(anchor_lang::ToAccountInfos::to_account_infos(&self.funding_mint));
 account_infos.extend(anchor_lang::ToAccountInfos::to_account_infos(&self.curve));
 account_infos.extend(anchor_lang::ToAccountInfos::to_account_infos(&self.payer_funding_ata));
 account_infos.extend(anchor_lang::ToAccountInfos::to_account_infos(&self.curve_funding_vault));
 account_infos.extend(anchor_lang::ToAccountInfos::to_account_infos(&self.funding_token_program));
 account_infos.extend(anchor_lang::ToAccountInfos::to_account_infos(&self.associated_token_program));
 account_infos
 }
}
