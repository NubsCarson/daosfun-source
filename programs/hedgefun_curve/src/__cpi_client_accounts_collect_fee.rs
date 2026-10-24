use anchor_lang::prelude::*;
pub struct CollectFee<'info> {
pub payer: AccountInfo<'info>,
pub funding_mint: AccountInfo<'info>,
pub depositor: AccountInfo<'info>,
pub recipient: AccountInfo<'info>,
pub curve: AccountInfo<'info>,
pub funding_recipient_acc: AccountInfo<'info>,
pub funding_vault: AccountInfo<'info>,
pub funding_token_program: AccountInfo<'info>,
pub associated_token_program: AccountInfo<'info>,
}
impl<'info> ToAccountMetas for CollectFee<'info> { fn to_account_metas(&self, _is_signer: Option<bool>) -> Vec<anchor_lang::solana_program::instruction::AccountMeta> { let mut account_metas=vec![];
account_metas.push(anchor_lang::solana_program::instruction::AccountMeta::new_readonly(anchor_lang::Key::key(&self.payer), true));
account_metas.push(anchor_lang::solana_program::instruction::AccountMeta::new_readonly(anchor_lang::Key::key(&self.funding_mint), false));
account_metas.push(anchor_lang::solana_program::instruction::AccountMeta::new_readonly(anchor_lang::Key::key(&self.depositor), false));
account_metas.push(anchor_lang::solana_program::instruction::AccountMeta::new_readonly(anchor_lang::Key::key(&self.recipient), false));
account_metas.push(anchor_lang::solana_program::instruction::AccountMeta::new(anchor_lang::Key::key(&self.curve), false));
account_metas.push(anchor_lang::solana_program::instruction::AccountMeta::new(anchor_lang::Key::key(&self.funding_recipient_acc), false));
account_metas.push(anchor_lang::solana_program::instruction::AccountMeta::new(anchor_lang::Key::key(&self.funding_vault), false));
account_metas.push(anchor_lang::solana_program::instruction::AccountMeta::new_readonly(anchor_lang::Key::key(&self.funding_token_program), false));
account_metas.push(anchor_lang::solana_program::instruction::AccountMeta::new_readonly(anchor_lang::Key::key(&self.associated_token_program), false));
account_metas } }
impl<'info> ToAccountInfos<'info> for CollectFee<'info> { fn to_account_infos(&self) -> Vec<AccountInfo<'info>> { let mut account_infos=vec![];
account_infos.extend(anchor_lang::ToAccountInfos::to_account_infos(&self.payer));
account_infos.extend(anchor_lang::ToAccountInfos::to_account_infos(&self.funding_mint));
account_infos.extend(anchor_lang::ToAccountInfos::to_account_infos(&self.depositor));
account_infos.extend(anchor_lang::ToAccountInfos::to_account_infos(&self.recipient));
account_infos.extend(anchor_lang::ToAccountInfos::to_account_infos(&self.curve));
account_infos.extend(anchor_lang::ToAccountInfos::to_account_infos(&self.funding_recipient_acc));
account_infos.extend(anchor_lang::ToAccountInfos::to_account_infos(&self.funding_vault));
account_infos.extend(anchor_lang::ToAccountInfos::to_account_infos(&self.funding_token_program));
account_infos.extend(anchor_lang::ToAccountInfos::to_account_infos(&self.associated_token_program));
account_infos } }
