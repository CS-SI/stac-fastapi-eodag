# -*- coding: utf-8 -*-
# Copyright 2025, CS GROUP - France, https://www.cs-soprasteria.com
#
# This file is part of stac-fastapi-eodag project
#     https://www.github.com/CS-SI/stac-fastapi-eodag
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.
"""Unit tests for telemetry module.

These tests verify that the telemetry functions can be
initialized without errors, and that tracer and meter providers
are correctly set up using in-memory exporters.
"""

import pytest
from fastapi import FastAPI
from opentelemetry import metrics, trace
from opentelemetry.sdk.metrics.export import InMemoryMetricReader
from opentelemetry.sdk.resources import Resource
from opentelemetry.sdk.trace.export import SimpleSpanProcessor
from opentelemetry.sdk.trace.export.in_memory_span_exporter import InMemorySpanExporter

from stac_fastapi.eodag.telemetry import (
    create_meter_provider,
    create_tracer_provider,
    instrument_eodag,
    instrument_fastapi,
)


@pytest.fixture
def resource() -> Resource:
    """Fixture returning a test Resource.

    :return: resource with test service name
    """
    return Resource.create({"service.name": "test-service"})


def test_create_tracer_provider(resource: Resource) -> None:
    """Test that ``create_tracer_provider`` sets up a tracer provider and records spans.

    :param resource: fixture providing a test Resource
    """
    # Patch exporter to in-memory
    exporter = InMemorySpanExporter()
    tracer_provider = create_tracer_provider(resource)
    tracer_provider.add_span_processor(SimpleSpanProcessor(exporter))

    tracer = trace.get_tracer("test")
    with tracer.start_as_current_span("test-span"):
        pass

    spans = exporter.get_finished_spans()
    assert len(spans) == 1
    assert spans[0].name == "test-span"


def test_create_meter_provider(resource: Resource, monkeypatch: pytest.MonkeyPatch) -> None:
    """Test that ``create_meter_provider`` sets up a meter provider and records metrics.

    :param resource: fixture providing a test Resource
    :param monkeypatch: pytest fixture to patch dependencies
    """
    reader = InMemoryMetricReader()

    # Monkeypatch PeriodicExportingMetricReader to return our InMemoryMetricReader
    monkeypatch.setattr(
        "stac_fastapi.eodag.telemetry.PeriodicExportingMetricReader",
        lambda exporter=None: reader,
    )

    # Call the function (will use patched reader)
    meter_provider = create_meter_provider(resource)

    # Ensure it’s registered
    metrics.set_meter_provider(meter_provider)

    meter = metrics.get_meter("test")
    counter = meter.create_counter("test_counter")
    counter.add(1)

    reader.collect()
    collected = reader.get_metrics_data()

    assert collected is not None
    assert any(record.resource.attributes["service.name"] == "test-service" for record in collected.resource_metrics)


def test_instrument_fastapi_runs() -> None:
    """Test that ``instrument_fastapi`` runs without raising errors.

    :param resource: fixture providing a test Resource
    """
    app = FastAPI()
    instrument_fastapi(app)


def test_instrument_eodag_runs(monkeypatch: pytest.MonkeyPatch) -> None:
    """Test that ``instrument_eodag`` runs without raising errors.

    The real :class:`EODAGInstrumentor` is monkeypatched to avoid
    external dependencies.

    :param monkeypatch: pytest fixture for monkeypatching
    """

    class DummyEODAG:
        pass

    class DummyInstrumentor:
        def __init__(self, api):
            self.api = api

        def instrument(self, tracer_provider, meter_provider):
            return "ok"

    # Patch the EODAGInstrumentor used inside your module
    monkeypatch.setattr("stac_fastapi.eodag.telemetry.EODAGInstrumentor", DummyInstrumentor)

    eodag = DummyEODAG()
    instrument_eodag(eodag)
