from pathlib import Path

from app.engine.masker import MaskingEngine


CONFIG_DIR = Path(__file__).resolve().parents[1] / 'config'


def test_masker_should_mask_regex_and_dictionary_terms():
    engine = MaskingEngine(CONFIG_DIR)
    text = '张三手机号13812345678，邮箱test@example.com，身份证110101199001011234，银行卡6222021234567890123，某客户公司已签约。'
    masked, details = engine.desensitize_text(text, location='text:1')

    assert '138****5678' in masked
    assert 'te***@example.com' in masked
    assert '110101********1234' in masked
    assert '6222' in masked and '0123' in masked
    assert '某客户公司' not in masked
    assert len(details) >= 5


def test_masker_should_mask_person_context_and_org_suffix_rules():
    engine = MaskingEngine(CONFIG_DIR)
    text = '联系人王小明老师已确认，由李四跟进，合作方星海集团今天到场。'
    masked, details = engine.desensitize_text(text, location='text:2')

    assert '王小明' not in masked
    assert '王*明' in masked
    assert '李四' not in masked
    assert '*四' in masked
    assert '星海集团' not in masked

    rule_types = {detail.rule_type for detail in details}
    assert 'person_context' in rule_types
    assert 'dictionary_group' in rule_types or 'org_suffix' in rule_types


def test_masker_report_should_distinguish_hit_types():
    engine = MaskingEngine(CONFIG_DIR)
    text = '客户赵敏经理邮箱zhaomin@example.com，就职于测试科技。'
    masked, details = engine.desensitize_text(text, location='text:3')

    assert '*敏' in masked
    assert any(detail.rule_type == 'person_context' and detail.entity_type == 'PERSON_NAME' for detail in details)
    assert any(detail.rule_type == 'regex' and detail.entity_type == 'EMAIL' for detail in details)
    assert any(detail.entity_type == 'ORGANIZATION_NAME' for detail in details)


def test_strict_profile_should_match_more_context_and_suffixes():
    light_engine = MaskingEngine(CONFIG_DIR, profile='light')
    strict_engine = MaskingEngine(CONFIG_DIR, profile='strict')
    text = '员工赵敏女士来自北辰研究院。'

    light_masked, _ = light_engine.desensitize_text(text, location='text:4')
    strict_masked, strict_details = strict_engine.desensitize_text(text, location='text:4')

    assert '赵敏' in light_masked or '北辰研究院' in light_masked
    assert '赵敏' not in strict_masked
    assert '北辰研究院' not in strict_masked
    assert any(detail.rule_type in {'person_context', 'org_suffix'} for detail in strict_details)


def test_org_suffix_should_mask_bureau_bank_branch_and_hospital():
    strict_engine = MaskingEngine(CONFIG_DIR, profile='strict')
    text = '呼和浩特市公安局、招商银行北京分行、招商银行上海支行、协和医院都需要脱敏。'

    masked, details = strict_engine.desensitize_text(text, location='text:6')

    assert '呼和浩特市公安局' not in masked
    assert '招商银行北京分行' not in masked
    assert '招商银行上海支行' not in masked
    assert '协和医院' not in masked


def test_org_suffix_should_mask_school_authority_and_finance_units():
    strict_engine = MaskingEngine(CONFIG_DIR, profile='strict')
    text = '北京大学、朝阳区人民法院、海淀区检察院、幸福路派出所、第一中学、风险管理委员会、税务局、招商证券、平安保险、创新基金、第一幼儿园都需要脱敏。'

    masked, details = strict_engine.desensitize_text(text, location='text:7')

    assert '北京大学' not in masked
    assert '朝阳区人民法院' not in masked
    assert '海淀区检察院' not in masked
    assert '幸福路派出所' not in masked
    assert '第一中学' not in masked
    assert '风险管理委员会' not in masked
    assert '税务局' not in masked
    assert '招商证券' not in masked
    assert '平安保险' not in masked
    assert '创新基金' not in masked
    assert '第一幼儿园' not in masked


def test_org_suffix_should_support_whitelist_and_rule_hint():
    strict_engine = MaskingEngine(CONFIG_DIR, profile='strict')
    text = '这里说的是学校和政府这两个泛词，不该脱敏；北京大学和朝阳区人民法院应该脱敏。'

    masked, details = strict_engine.desensitize_text(text, location='text:8')

    assert '学校和政府这两个泛词' in masked
    assert '北京大学' not in masked
    assert '朝阳区人民法院' not in masked
    assert any(detail.rule_type == 'org_suffix' and detail.rule_hint in {'大学', '法院'} for detail in details)
