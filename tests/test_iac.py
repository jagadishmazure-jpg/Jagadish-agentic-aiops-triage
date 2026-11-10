"""Infrastructure is written, not run: Terraform and Bicep stay in step, and the deploy path is gated."""

import re

from conftest import ROOT

TF = (ROOT / "infra/terraform/main.tf").read_text()
TF_VARS = (ROOT / "infra/terraform/variables.tf").read_text()
BICEP = (ROOT / "infra/bicep/main.bicep").read_text()
DEPLOY = (ROOT / ".github/workflows/deploy.yml").read_text()
PIPELINE = (ROOT / "infra/aml/pipeline.yml").read_text()

TF_TO_ARM = {
    "azurerm_log_analytics_workspace": "Microsoft.OperationalInsights/workspaces",
    "azurerm_application_insights": "Microsoft.Insights/components",
    "azurerm_storage_account": "Microsoft.Storage/storageAccounts",
    "azurerm_key_vault": "Microsoft.KeyVault/vaults",
    "azurerm_monitor_diagnostic_setting": "Microsoft.Insights/diagnosticSettings",
    "azurerm_role_assignment": "Microsoft.Authorization/roleAssignments",
}


def tf_types():
    out = [TF_TO_ARM[k] for k in re.findall(r'^resource "(\w+)"', TF, re.M) if k in TF_TO_ARM]
    return sorted(out + re.findall(r'type\s*=\s*"([\w./]+)@', TF))


def test_terraform_and_bicep_create_the_same_resources():
    assert tf_types() == sorted(re.findall(r"^resource \w+ '([\w./]+)@", BICEP, re.M))


def test_cluster_scales_to_zero_with_no_ssh_or_local_auth_in_both_stacks():
    for text in ("minNodeCount", "PT2M", "Disabled", "disableLocalAuth"):
        assert text in TF and text in BICEP, text
    assert re.search(r"minNodeCount\s*=\s*0", TF) and "minNodeCount: 0" in BICEP
    assert "shared_access_key_enabled       = false" in TF and "allowSharedKeyAccess: false" in BICEP


def test_node_count_is_capped_and_cluster_gets_only_storage_access():
    assert "var.max_nodes <= 2" in TF_VARS and "@maxValue(2)" in BICEP
    assert TF.count('resource "azurerm_role_assignment"') == 1
    assert 'role_definition_name = "Storage Blob Data Contributor"' in TF
    assert "ba92f5b4-2d11-453d-a403-e96b0029c9fe" in BICEP


def test_cpu_cluster_size_matches_in_both_stacks():
    assert '"Standard_D8s_v5"' in TF_VARS and "'Standard_D8s_v5'" in BICEP
    assert "cpu-triage" in TF and "cpu-triage" in BICEP


def test_pipeline_reruns_the_same_triage_code_and_scores_it():
    assert "default_compute: azureml:cpu-triage" in PIPELINE and "run_eval.py --runs-only" in PIPELINE
    assert "fetch_models.sh" in PIPELINE and ":latest" not in PIPELINE
    from aiops.agent import CONFIGS, RULES

    for c in re.search(r"for c in ([^;]+);", PIPELINE).group(1).split():
        assert c in CONFIGS or c in RULES, c


def test_deploy_workflow_is_manual_gated_and_oidc():
    assert re.search(r"^on:\n  workflow_dispatch:", DEPLOY, re.M) and "push:" not in DEPLOY
    jobs = re.findall(r"^  ([\w-]+):\n", DEPLOY.split("\njobs:\n", 1)[1], re.M)
    for job in jobs:
        if job != "preflight":
            block = DEPLOY.split(f"\n  {job}:\n", 1)[1]
            assert "if: vars.DEPLOY_ENABLED == 'true'" in block.split("steps:")[0], job
    assert "id-token: write" in DEPLOY and "secrets." not in DEPLOY


def test_all_actions_pinned_to_full_sha():
    for wf in (ROOT / ".github/workflows").glob("*.yml"):
        for ref in re.findall(r"uses:\s*[\w.-]+/[\w./-]+@(\S+)", wf.read_text()):
            assert re.fullmatch(r"[0-9a-f]{40}", ref), (wf.name, ref)


def test_codeql_is_skipped_while_the_repository_is_private():
    q = (ROOT / ".github/workflows/codeql.yml").read_text()
    assert "!github.event.repository.private" in q
