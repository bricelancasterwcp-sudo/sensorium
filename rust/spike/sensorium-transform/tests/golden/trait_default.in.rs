trait Greeter {
    fn name(&self) -> String;

    fn greet(&self) -> String {
        format!("hello {}", self.name())
    }
}
