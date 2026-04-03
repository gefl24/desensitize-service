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
    assert '李四' not in masked
    assert '星海集团' not in masked

    rule_types = {detail.rule_type for detail in details}
    assert 'person_context' in rule_types
    assert 'dictionary_group' in rule_types or 'org_suffix' in rule_types


def test_masker_report_should_distinguish_hit_types():
    engine = MaskingEngine(CONFIG_DIR)
    text = '客户赵敏经理邮箱zhaomin@example.com，就职于测试科技。'
    _, details = engine.desensitize_text(text, location='text:3')

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


def test_org_suffix_should_keep_first_five_chars():
    strict_engine = MaskingEngine(CONFIG_DIR, profile='strict')
    text = '内蒙古盛昱电子科技有限公司已签约。'

    masked, details = strict_engine.desensitize_text(text, location='text:5')

    assert '内蒙古盛昱' in masked
    assert '内蒙古盛昱电子科技有限公司' not in masked
    assert any(detail.rule_type == 'org_suffix' and detail.masked_preview.startswith('内蒙古盛昱') and '*' in detail.masked_preview for detail in details)
