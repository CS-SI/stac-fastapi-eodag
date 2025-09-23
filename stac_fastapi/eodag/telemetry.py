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
"""module for opentelemetry instrumentation"""

from __future__ import annotations

import logging
from typing import Union

from fastapi import FastAPI
from opentelemetry import metrics, trace
from opentelemetry.exporter.otlp.proto.http.metric_exporter import OTLPMetricExporter
from opentelemetry.exporter.otlp.proto.http.trace_exporter import OTLPSpanExporter
from opentelemetry.instrumentation.eodag import EODAGInstrumentor
from opentelemetry.instrumentation.fastapi import FastAPIInstrumentor
from opentelemetry.sdk.metrics import MeterProvider
from opentelemetry.sdk.metrics._internal.export import PeriodicExportingMetricReader
from opentelemetry.sdk.resources import Resource
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import BatchSpanProcessor

logger = logging.getLogger(__name__)


def get_resource(app: FastAPI) -> Resource:
    """create opentelemetry resource"""
    if not getattr(app.state, "resource", None):
        app.state.otel_resource = Resource.create().merge(Resource.create({"service.name": "stac-fastapi-eodag"}))

    return app.state.otel_resource


def get_tracer_provider(resource: Resource) -> Union[TracerProvider, trace.TracerProvider]:
    """create opentelemetry tracer provider"""
    tracer_provider = trace.get_tracer_provider()
    if tracer_provider and not isinstance(tracer_provider, trace.ProxyTracerProvider):
        return tracer_provider

    tracer_provider = TracerProvider(resource=resource)
    processor = BatchSpanProcessor(OTLPSpanExporter())
    tracer_provider.add_span_processor(processor)
    trace.set_tracer_provider(tracer_provider)

    return tracer_provider


def get_meter_provider(resource: Resource) -> Union[MeterProvider, metrics.MeterProvider]:
    """create opentelemetry meter provider"""
    meter_provider = metrics.get_meter_provider()
    if meter_provider and not isinstance(meter_provider, metrics._internal._ProxyMeterProvider):
        return meter_provider

    reader = PeriodicExportingMetricReader(OTLPMetricExporter())
    meter_provider = MeterProvider(resource=resource, metric_readers=[reader])
    metrics.set_meter_provider(meter_provider)

    return meter_provider


def instrument_fastapi(app: FastAPI):
    """Instrument FastAPI app."""
    logger.info("Instrument FastAPI app")
    resource = get_resource(app)

    FastAPIInstrumentor.instrument_app(
        app=app,
        tracer_provider=get_tracer_provider(resource),
        meter_provider=get_meter_provider(resource),
    )


def instrument_eodag(app: FastAPI):
    """Instrument EODAG app"""
    logger.info("Instrument EODAG app")
    resource = get_resource(app)

    EODAGInstrumentor(app.state.dag).instrument(
        tracer_provider=get_tracer_provider(resource),
        meter_provider=get_meter_provider(resource),
    )
