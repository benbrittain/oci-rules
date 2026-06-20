load("//tar:toolchain.bzl", "TarToolchainInfo")

def _tar_file_impl(ctx: AnalysisContext) -> list[Provider]:
    tar_output_name = (
        ctx.attrs.out if ctx.attrs.out else "{}.tar".format(ctx.label.name)
    )
    tar_file = ctx.actions.declare_output(tar_output_name)

    # Each manifest entry maps a source to its path inside the archive. `srcs`
    # land at the root under their basename with their on-disk mode; `files`
    # place a source at an explicit arcname with an optional mode override.
    manifest = [
        {"arcname": src.basename, "mode": None, "src": src}
        for src in ctx.attrs.srcs
    ] + [
        {"arcname": dst, "mode": ctx.attrs.mode, "src": src}
        for dst, src in ctx.attrs.files.items()
    ]

    # with_inputs ties the referenced source artifacts to the action so they
    # are materialised before the helper reads them.
    manifest_file = ctx.actions.write_json(
        "manifest.json",
        manifest,
        with_inputs = True,
    )

    # this is not GNU tar. don't look these flags up in the manual.
    cmd = cmd_args(
        ctx.attrs._tar_toolchain[TarToolchainInfo].tar[RunInfo],
        "--compress",
        "true" if ctx.attrs.compress else "false",
        "--manifest",
        manifest_file,
        "--filename",
        tar_file.as_output(),
    )

    ctx.actions.run(cmd, category = "tar")

    return [DefaultInfo(default_output = tar_file)]

tar_file = rule(
    impl = _tar_file_impl,
    attrs = {
        "compress": attrs.bool(default = False),
        "files": attrs.dict(
            key = attrs.string(),
            value = attrs.source(),
            default = {},
        ),
        "mode": attrs.option(attrs.string(), default = None),
        "out": attrs.option(attrs.string(), default = None),
        "srcs": attrs.list(attrs.source(), default = []),
        "_tar_toolchain": attrs.toolchain_dep(
            default = "toolchains//:tar",
            providers = [TarToolchainInfo],
        ),
    },
)
