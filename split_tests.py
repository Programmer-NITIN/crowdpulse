import os
import re

TEST_DIR = 'tests'
MEGA_FILE = os.path.join(TEST_DIR, 'test_coverage_boost.py')

with open(MEGA_FILE, 'r', encoding='utf-8') as f:
    content = f.read()

# Split the content into header (imports) and the rest
parts = re.split(r'\n# ═+\n', content)
header = parts[0].strip()

# Mapping of class names to files
file_maps = {
    'TestGeminiCaller': 'test_ai_engine_edge.py',
    'TestExplainerLive': 'test_ai_engine_edge.py',
    'TestChatbotLive': 'test_ai_engine_edge.py',
    'TestStaffAdvisorLive': 'test_ai_engine_edge.py',
    'TestPromptBuilderBranches': 'test_ai_engine_edge.py',
    'TestFirestoreLive': 'test_google_services_mocked.py',
    'TestBigQueryLive': 'test_google_services_mocked.py',
    'TestMapsLive': 'test_google_services_mocked.py',
    'TestCloudLoggingLive': 'test_google_services_mocked.py',
    'TestFirebaseAuthLive': 'test_google_services_mocked.py',
    'TestDecisionEngineEdgeCases': 'test_decision_engine_edge.py',
    'TestCrowdEngineEdgeCases': 'test_crowd_engine_edge.py',
    'TestConfigValidators': 'test_config_validators.py',
    'TestRateLimiterIsRateLimited': 'test_middleware_edge.py',
    'TestMainLifespan': 'test_main_edge.py',
}

files_content = {}
for file_name in file_maps.values():
    if file_name not in files_content:
        files_content[file_name] = header + "\n\n"

for part in parts[1:]:
    if not part.strip():
        continue
    match = re.search(r'class\s+([A-Za-z0-9_]+)', part)
    if match:
        class_name = match.group(1)
        target_file = file_maps.get(class_name)
        if target_file:
            files_content[target_file] += "\n# " + ("═" * 70) + "\n"
            files_content[target_file] += part.rstrip() + "\n\n"
        else:
            print(f"Unknown class {class_name}")

for file_name, file_content in files_content.items():
    with open(os.path.join(TEST_DIR, file_name), 'w', encoding='utf-8') as f:
        f.write(file_content)

os.remove(MEGA_FILE)
print("Split successful!")
