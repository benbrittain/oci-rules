TarToolchainInfo = provider(
    fields={
        "tar_file": typing.Any,
    }
)


def tar_toolchain_impl(ctx) -> list[[DefaultInfo, TarToolchainInfo]]:
    """
    A Tar toolchain.
    """
    return [
        DefaultInfo(),
        TarToolchainInfo(
            tar_file=ctx.attrs._tar_file,
        ),
    ]


tar_toolchain = rule(
    impl=tar_toolchain_impl,
    attrs={
        "_tar_file": attrs.dep(
            default="root//tar:tar_file.py",
        ),
    },
    is_toolchain_rule=True,
)
