//! Seeded bug: the buffer is meant to alert before it can overrun, but the
//! alert fires at `used > 100` while the buffer's real high-water mark is
//! 99. `alert` is therefore never called, the program exits 0, and the run
//! looks perfectly healthy from the outside.

fn alert(used: usize) -> usize {
    used
}

fn fill(buf: &mut Vec<u8>, chunk: usize) -> usize {
    buf.resize(buf.len() + chunk, 0);
    let used = buf.len();
    if used > 100 {
        // BUG: the buffer's capacity is 100, so the guard must be `>=`.
        alert(used);
    }
    used
}

fn drain(buf: &mut Vec<u8>, n: usize) -> usize {
    buf.drain(..n);
    buf.len()
}

fn main() {
    let mut buf = Vec::new();
    for (chunk, n) in [(40, 0), (30, 10), (25, 20), (34, 30), (0, 69)] {
        fill(&mut buf, chunk);
        drain(&mut buf, n);
    }
    println!("done; buffer left holding {} bytes", buf.len());
}
