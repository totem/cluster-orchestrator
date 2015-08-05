import json
import datetime
from nose.tools import eq_
import pytz
from orchestrator.views.util import DateTimeEncoder

NOW = datetime.datetime(2022, 01, 01, hour=0, minute=0, second=0,
                        microsecond=0, tzinfo=pytz.UTC)


def test_datetime_encoder_for_date_obj():
    # When: I encode datetime using json encoder
    output = json.dumps(NOW, cls=DateTimeEncoder)

    # Then: Output gets serialized as expected
    eq_(output, '"2022-01-01T00:00:00+00:00"')


def test_datetime_encoder_for_non_date_obj():
    # When: I encode datetime using json encoder
    output = json.dumps(5, cls=DateTimeEncoder)

    # Then: Output gets serialized as expected
    eq_(output, '5')
