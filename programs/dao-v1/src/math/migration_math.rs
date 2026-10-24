//! Reconstructed helpers; blank lines and call columns preserve observed panic locations.
//! Source names are provisional. Do not rustfmt when comparing exact builds.
use num_bigint::BigUint;
use num_traits::ToPrimitive;
use rust_decimal::{Decimal, MathematicalOps};
























#[inline(never)]
pub fn get_initial_sqrt_price(
    amount_a: u128,
    amount_b: u128,
    sqrt_min: u128,
    sqrt_max: u128,
) -> u128 {
    if amount_a == 0 || amount_b == 0 {
        panic!("Amount cannot be zero");
    }
    let q = Decimal::from(1u64 << 63) * Decimal::from(2u64);
    let amount_a = Decimal::from(amount_a);
    let amount_b = Decimal::from(amount_b);
    let min = Decimal::from(sqrt_min) / q;
    let max = Decimal::from(sqrt_max) / q;
    let inverse_max = Decimal::ONE / max;
    let ratio = amount_b / amount_a;
    let term = inverse_max * ratio;
    let b = min - term;
    let negative_b = term - min;
    let four_ratio = Decimal::from(4u64) * ratio;
    let discriminant = negative_b * negative_b + four_ratio;






    let sqrt = discriminant.sqrt()             .expect("Failed to compute sqrt");
    let quotient = (b + sqrt) / Decimal::from(2u64);
    let value = (quotient * q).floor();

    value.to_u128()        .expect("Conversion failed")
}















#[inline(never)]
pub fn liquidity_from_a(amount: u128, sqrt_price: u128, sqrt_max: u128) -> u128 {
    let numerator = BigUint::from(amount) * BigUint::from(sqrt_price) * BigUint::from(sqrt_max);
    let denominator = BigUint::from(sqrt_max) - BigUint::from(sqrt_price);
    let value = numerator / denominator;







    value.to_u128()                   .unwrap()
}
#[inline(never)]
pub fn liquidity_from_b(amount: u128, sqrt_min: u128, sqrt_price: u128) -> u128 {
    let denominator = BigUint::from(sqrt_price) - BigUint::from(sqrt_min);
    let numerator = BigUint::from(amount) << 128usize;
    let value = numerator / denominator;





    value.to_u128()                   .unwrap()
}
