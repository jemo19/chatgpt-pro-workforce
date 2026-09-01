PYTHON ?= python3
SKILL_DIR ?= chatgpt-pro-workforce
SKILL_CREATOR ?= $(HOME)/.codex/skills/.system/skill-creator

.PHONY: check validate validate-authoritative test check-public package

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

check-public:
	$(PYTHON) scripts/check_public_tree.py .

package:
	$(PYTHON) scripts/package_skill.py $(SKILL_DIR) --output dist/chatgpt-pro-workforce.zip
