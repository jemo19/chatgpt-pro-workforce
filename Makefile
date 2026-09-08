PYTHON ?= python3
SKILL_DIR ?= chatgpt-pro-workforce
SKILL_CREATOR ?= $(HOME)/.codex/skills/.system/skill-creator

# Keep validation and packaging from mutating the source tree with bytecode.
export PYTHONDONTWRITEBYTECODE := 1

.PHONY: check validate validate-authoritative test check-public package verify-package

check: validate test check-public

validate:
	$(PYTHON) tests/validate_skill.py $(SKILL_DIR)

validate-authoritative:
	test -f "$(SKILL_CREATOR)/scripts/quick_validate.py"
	$(PYTHON) "$(SKILL_CREATOR)/scripts/quick_validate.py" "$(SKILL_DIR)"

test:
	$(PYTHON) tests/test_behavior.py $(SKILL_DIR)
	$(PYTHON) tests/test_forward.py $(SKILL_DIR)
	$(PYTHON) tests/test_status_dashboard.py $(SKILL_DIR)
	$(PYTHON) tests/test_research_explorer.py $(SKILL_DIR)
	$(PYTHON) tests/test_obsidian_locator.py $(SKILL_DIR)
	$(PYTHON) tests/test_run_state.py $(SKILL_DIR)
	$(PYTHON) tests/test_artifact_store.py $(SKILL_DIR)
	$(PYTHON) tests/test_package_skill.py .

check-public:
	$(PYTHON) scripts/check_public_tree.py .

package: check
	$(PYTHON) scripts/package_skill.py $(SKILL_DIR) --output dist/chatgpt-pro-workforce.zip

verify-package: package
	$(PYTHON) scripts/package_skill.py --verify-only --output dist/chatgpt-pro-workforce.zip
