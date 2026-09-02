//! Lifetime keys-typed counter, persisted next to the Python host file.
//!
//! Path: ~/Library/Application Support/BongoCat/keys_typed.json
//! Format: {"keys_typed": 12345}

use std::fs;
use std::io::Write;
use std::path::PathBuf;
use std::time::{Duration, Instant};

const SAVE_INTERVAL: Duration = Duration::from_secs(2);

pub struct KeyCounter {
    path: PathBuf,
    total: u64,
    dirty: bool,
    last_save: Instant,
}

impl KeyCounter {
    pub fn load() -> Self {
        let path = default_path();
        let total = read_total(&path);
        Self {
            path,
            total,
            dirty: false,
            last_save: Instant::now(),
        }
    }

    pub fn total(&self) -> u64 {
        self.total
    }

    pub fn add(&mut self, n: u64) -> u64 {
        if n == 0 {
            return self.total;
        }
        self.total += n;
        self.dirty = true;
        self.total
    }

    pub fn maybe_flush(&mut self) {
        if !self.dirty {
            return;
        }
        if self.last_save.elapsed() < SAVE_INTERVAL {
            return;
        }
        self.flush();
    }

    pub fn flush(&mut self) {
        if let Some(parent) = self.path.parent() {
            let _ = fs::create_dir_all(parent);
        }
        let body = format!("{{\n  \"keys_typed\": {}\n}}\n", self.total);
        let tmp = self.path.with_extension("json.tmp");
        if let Ok(mut f) = fs::File::create(&tmp) {
            let _ = f.write_all(body.as_bytes());
            let _ = f.sync_all();
        }
        let _ = fs::rename(&tmp, &self.path);
        self.dirty = false;
        self.last_save = Instant::now();
    }
}

fn default_path() -> PathBuf {
    let home = std::env::var("HOME").unwrap_or_else(|_| ".".into());
    PathBuf::from(home)
        .join("Library")
        .join("Application Support")
        .join("BongoCat")
        .join("keys_typed.json")
}

fn read_total(path: &PathBuf) -> u64 {
    let Ok(text) = fs::read_to_string(path) else {
        return 0;
    };
    parse_keys_typed(&text)
}

fn parse_keys_typed(text: &str) -> u64 {
    let Some(idx) = text.find("\"keys_typed\"") else {
        return 0;
    };
    let rest = &text[idx + 12..];
    let Some(colon) = rest.find(':') else {
        return 0;
    };
    let digits: String = rest[colon + 1..]
        .chars()
        .skip_while(|c| !c.is_ascii_digit())
        .take_while(|c| c.is_ascii_digit())
        .collect();
    digits.parse().unwrap_or(0)
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn parse_valid_json() {
        assert_eq!(parse_keys_typed("{\n  \"keys_typed\": 12\n}\n"), 12);
    }

    #[test]
    fn parse_missing_is_zero() {
        assert_eq!(parse_keys_typed("{}"), 0);
        assert_eq!(parse_keys_typed("nope"), 0);
    }
}
