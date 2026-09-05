@Wpub fn line_doc() -> u8 {
    //! An inner line doc comment.
@G(7)    @R(7)1@E
}

pub fn block_doc() -> u8 {
    /*! An inner block doc comment. */@G(8)
    @R(8)2@E
}@U
