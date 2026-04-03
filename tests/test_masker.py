from pathlib import Path

from app.engine.masker import MaskingEngine


def test_masker_should_mask_regex_and_dictionary_terms():
    engine = MaskingEngine(Path(__file__).resolve().parents[1] / 'config')
    text = '张三手机号13812345678，邮箱test@example.com，身份证110101199001011234，银行卡6222021234567890123，某客户公司已签约。'
    masked, details = engine.desensitize_text(text, location='text:1')

    assert '138****5678' in masked
    assert 'te***@example.com' in masked
    assert '110101********1234' in masked
    assert '6222' in masked and '0123' in masked
    assert '某客户公司' not in masked
    assert len(details) >= 5


def test_masker_should_mask_person_context_and_org_suffix_rules():
    engine = MaskingEngine(Path(__file__).resolve().parents[1] / 'config')
    text = '联系人王小明老师已确认，由李四跟进，合作方星海集团今天到场。'
    masked, details = engine.desensitize_text(text, location='text:2')

    assert '王小明' not in masked
    assert '李四' not in masked
    assert '星海集团' not in masked

    rule_types = {detail.rule_type for detail in details}
    assert 'person_context' in rule_types
    assert 'dictionary_group' in rule_types or 'org_suffix' in rule_types


def test_masker_report_should_distinguish_hit_types():
    engine = MaskingEngine(Path(__file__).resolve().parents[1] / 'config')
    text = '客户赵敏经理邮箱zhaomin@example.com，就职于测试科技。'
    _, details = engine.desensitize_text(text, location='text:3')

    assert any(detail.rule_type == 'person_context' and detail.entity_type == 'PERSON_NAME' for detail in details)
    assert any(detail.rule_type == 'regex' and detail.entity_type == 'EMAIL' for detail in details)
    assert any(detail.entity_type == 'ORGANIZATION_NAME' for detail in details)
