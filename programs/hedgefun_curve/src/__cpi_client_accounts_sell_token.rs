use anchor_lang::prelude::*;
pub struct SellToken<'info> {
pub signer: AccountInfo<'info>,
pub depositor: AccountInfo<'info>,
pub token_mint: AccountInfo<'info>,
pub funding_mint: AccountInfo<'info>,
pub curve: AccountInfo<'info>,
pub signer_token_acc: AccountInfo<'info>,
pub target_funding_acc: AccountInfo<'info>,
pub token_vault: AccountInfo<'info>,
pub funding_vault: AccountInfo<'info>,
pub token_program: AccountInfo<'info>,
pub funding_token_program: AccountInfo<'info>,
pub associated_token_program: AccountInfo<'info>,
}
impl<'info> ToAccountMetas for SellToken<'info> { fn to_account_metas(&self, _is_signer: Option<bool>) -> Vec<anchor_lang::solana_program::instruction::AccountMeta> { let mut account_metas=vec![];
account_metas.push(anchor_lang::solana_program::instruction::AccountMeta::new_readonly(anchor_lang::Key::key(&self.signer), true));
account_metas.push(anchor_lang::solana_program::instruction::AccountMeta::new_readonly(anchor_lang::Key::key(&self.depositor), false));
account_metas.push(anchor_lang::solana_program::instruction::AccountMeta::new_readonly(anchor_lang::Key::key(&self.token_mint), false));
account_metas.push(anchor_lang::solana_program::instruction::AccountMeta::new_readonly(anchor_lang::Key::key(&self.funding_mint), false));
account_metas.push(anchor_lang::solana_program::instruction::AccountMeta::new(anchor_lang::Key::key(&self.curve), false));
account_metas.push(anchor_lang::solana_program::instruction::AccountMeta::new(anchor_lang::Key::key(&self.signer_token_acc), false));
account_metas.push(anchor_lang::solana_program::instruction::AccountMeta::new(anchor_lang::Key::key(&self.target_funding_acc), false));
account_metas.push(anchor_lang::solana_program::instruction::AccountMeta::new(anchor_lang::Key::key(&self.token_vault), false));
account_metas.push(anchor_lang::solana_program::instruction::AccountMeta::new(anchor_lang::Key::key(&self.funding_vault), false));
account_metas.push(anchor_lang::solana_program::instruction::AccountMeta::new_readonly(anchor_lang::Key::key(&self.token_program), false));
account_metas.push(anchor_lang::solana_program::instruction::AccountMeta::new_readonly(anchor_lang::Key::key(&self.funding_token_program), false));
account_metas.push(anchor_lang::solana_program::instruction::AccountMeta::new_readonly(anchor_lang::Key::key(&self.associated_token_program), false));
account_metas } }
impl<'info> ToAccountInfos<'info> for SellToken<'info> { fn to_account_infos(&self) -> Vec<AccountInfo<'info>> { let mut account_infos=vec![];
account_infos.extend(anchor_lang::ToAccountInfos::to_account_infos(&self.signer));
account_infos.extend(anchor_lang::ToAccountInfos::to_account_infos(&self.depositor));
account_infos.extend(anchor_lang::ToAccountInfos::to_account_infos(&self.token_mint));
account_infos.extend(anchor_lang::ToAccountInfos::to_account_infos(&self.funding_mint));
account_infos.extend(anchor_lang::ToAccountInfos::to_account_infos(&self.curve));
account_infos.extend(anchor_lang::ToAccountInfos::to_account_infos(&self.signer_token_acc));
account_infos.extend(anchor_lang::ToAccountInfos::to_account_infos(&self.target_funding_acc));
account_infos.extend(anchor_lang::ToAccountInfos::to_account_infos(&self.token_vault));
account_infos.extend(anchor_lang::ToAccountInfos::to_account_infos(&self.funding_vault));
account_infos.extend(anchor_lang::ToAccountInfos::to_account_infos(&self.token_program));
account_infos.extend(anchor_lang::ToAccountInfos::to_account_infos(&self.funding_token_program));
account_infos.extend(anchor_lang::ToAccountInfos::to_account_infos(&self.associated_token_program));
account_infos } }
