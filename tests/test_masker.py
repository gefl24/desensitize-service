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
