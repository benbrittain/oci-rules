load("//oci:toolchain.bzl", "OciToolchainInfo")

def _oci_push_impl(ctx: AnalysisContext) -> list[Provider]:
    layout = ctx.attrs.image[DefaultInfo].default_outputs[0]
    crane = ctx.attrs._oci_toolchain[OciToolchainInfo].crane[RunInfo]

    repository = ctx.attrs.repository or ctx.label.package.split("/")[-1]
    ref = "{}/{}:{}".format(ctx.attrs.registry, repository, ctx.attrs.tag)

    cmd = cmd_args(crane, "push")
    if ctx.attrs.insecure:
        cmd.add("--insecure")
    cmd.add(layout, ref)

    return [DefaultInfo(), RunInfo(args = cmd)]

oci_push = rule(
    impl = _oci_push_impl,
    attrs = {
        "image": attrs.dep(providers = [DefaultInfo]),
        "registry": attrs.string(default = "localhost:5000"),
        "repository": attrs.option(attrs.string(), default = None),
        "tag": attrs.string(default = "dev"),
        "insecure": attrs.bool(default = True),
        "_oci_toolchain": attrs.toolchain_dep(
            default = "toolchains//:oci",
            providers = [OciToolchainInfo],
        ),
    },
)
