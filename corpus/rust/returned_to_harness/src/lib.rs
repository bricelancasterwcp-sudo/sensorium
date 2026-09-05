//! Seeded bug: the `height` setting was renamed and the test fixture was
//! not updated, so the test returns `Err` instead of failing an assertion.
//! libtest prints the `Debug` of the error and nothing else -- no frame, no
//! stack, no note of which of the two `?`s it came out of.

#[derive(Debug)]
pub struct Missing(pub String);

pub fn setting(name: &str) -> Result<u32, Missing> {
    match name {
        "width" => Ok(80),
        other => Err(Missing(other.to_string())),
    }
}

pub fn layout(name: &str) -> Result<u32, Missing> {
    let value = setting(name)?;
    Ok(value + 2)
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn the_width_setting_is_readable() {
        assert!(setting("width").is_ok());
    }

    #[test]
    fn the_default_layout_fits() -> Result<(), Missing> {
        let wide = layout("width")?;
        assert_eq!(wide, 82);
        // BUG: this setting is called `rows` now.
        let tall = layout("height")?;
        assert_eq!(tall, 26);
        Ok(())
    }
}
