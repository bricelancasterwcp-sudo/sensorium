pub trait Greeter {
    fn name(&self) -> String;

    fn greet(&self) -> String {@G(7)
        @R(7)format!("hello {}", self.name())@E
    }
}@U
