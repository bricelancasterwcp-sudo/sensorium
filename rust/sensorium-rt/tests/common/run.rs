//! Running the `scenario` binary: one subject process per falsification, with
//! its own environment and its own spool directory.

use std::path::Path;
use std::process::{Command, Output, Stdio};

// ---------------------------------------------------------------------------
// Running a scenario
// ---------------------------------------------------------------------------

pub struct Run {
    pub output: Output,
    pub pid: u32,
    pub stdout: String,
    pub stderr: String,
}

impl Run {
    /// The value the scenario printed as `<key> <value>`.
    pub fn says(&self, key: &str) -> String {
        self.stdout
            .lines()
            .find_map(|l| l.strip_prefix(&format!("{key} ")))
            .unwrap_or_else(|| panic!("scenario printed no {key:?} line; stdout: {}", self.stdout))
            .trim()
            .to_owned()
    }

    pub fn says_u64(&self, key: &str) -> u64 {
        self.says(key).parse().expect("a number")
    }
}

pub struct Spec<'a> {
    name: &'a str,
    args: Vec<&'a str>,
    dir: Option<&'a Path>,
    tier: Option<&'a str>,
    sandbox: Option<&'a Path>,
    env: Vec<(&'a str, String)>,
    allow_failure: bool,
}

impl<'a> Spec<'a> {
    pub fn new(name: &'a str) -> Spec<'a> {
        Spec {
            name,
            args: Vec::new(),
            dir: None,
            tier: None,
            sandbox: None,
            env: Vec::new(),
            allow_failure: false,
        }
    }

    pub fn arg(mut self, a: &'a str) -> Self {
        self.args.push(a);
        self
    }

    pub fn spool(mut self, d: &'a Path) -> Self {
        self.dir = Some(d);
        self
    }

    pub fn tier(mut self, t: &'a str) -> Self {
        self.tier = Some(t);
        self
    }

    pub fn sandbox(mut self, s: &'a Path) -> Self {
        self.sandbox = Some(s);
        self
    }

    pub fn env(mut self, k: &'a str, v: impl Into<String>) -> Self {
        self.env.push((k, v.into()));
        self
    }

    pub fn allow_failure(mut self) -> Self {
        self.allow_failure = true;
        self
    }

    fn command(&self) -> Command {
        let mut cmd = Command::new(env!("CARGO_BIN_EXE_scenario"));
        if let Some(s) = self.sandbox {
            cmd.current_dir(s);
            cmd.env("TMPDIR", s);
            cmd.env("HOME", s);
        }
        cmd.arg(self.name);
        cmd.args(&self.args);
        cmd.env_remove("SENSORIUM_SPOOL");
        cmd.env_remove("SENSORIUM_TIER");
        cmd.env_remove("SENSORIUM_TEST_SPOOL_LIMIT");
        if let Some(d) = self.dir {
            cmd.env("SENSORIUM_SPOOL", d);
        }
        if let Some(t) = self.tier {
            cmd.env("SENSORIUM_TIER", t);
        }
        for (k, v) in &self.env {
            cmd.env(k, v);
        }
        cmd
    }

    pub fn run(self) -> Run {
        let output = self
            .command()
            .output()
            .expect("running the scenario binary");
        let stdout = String::from_utf8_lossy(&output.stdout).into_owned();
        let stderr = String::from_utf8_lossy(&output.stderr).into_owned();
        if !self.allow_failure {
            assert!(
                output.status.success(),
                "scenario {} failed: {:?}\nstdout: {stdout}\nstderr: {stderr}",
                self.name,
                output.status
            );
        }
        let pid = stdout
            .lines()
            .find_map(|l| l.strip_prefix("pid "))
            .and_then(|s| s.trim().parse().ok())
            .unwrap_or_else(|| {
                panic!(
                    "scenario {} did not print its pid; stdout: {stdout}",
                    self.name
                )
            });
        Run {
            output,
            pid,
            stdout,
            stderr,
        }
    }

    /// Start the scenario, wait for it to create `ready`, then SIGKILL it.
    /// Returns its pid.
    pub fn run_and_kill(self, ready: &Path) -> u32 {
        let mut child = self
            .command()
            .stdout(Stdio::piped())
            .spawn()
            .expect("spawning the scenario binary");
        let pid = child.id();
        let deadline = std::time::Instant::now() + std::time::Duration::from_secs(20);
        while !ready.exists() {
            assert!(
                std::time::Instant::now() < deadline,
                "the scenario never signalled ready at {}",
                ready.display()
            );
            if let Ok(Some(st)) = child.try_wait() {
                panic!("the scenario exited ({st:?}) before signalling ready");
            }
            std::thread::sleep(std::time::Duration::from_millis(5));
        }
        // SIGKILL, which no destructor and no handler can intercept.
        child.kill().expect("SIGKILL");
        let st = child.wait().expect("reaping the scenario");
        assert!(
            !st.success(),
            "a SIGKILLed process cannot exit successfully"
        );
        pid
    }
}
