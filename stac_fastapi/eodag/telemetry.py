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
from typing import TYPE_CHECKING, Union

from opentelemetry import metrics, trace
from opentelemetry.exporter.otlp.proto.http.metric_exporter import OTLPMetricExporter
from opentelemetry.exporter.otlp.proto.http.trace_exporter import OTLPSpanExporter
from opentelemetry.instrumentation.eodag import EODAGInstrumentor
from opentelemetry.instrumentation.fastapi import FastAPIInstrumentor
from opentelemetry.sdk.metrics import MeterProvider
from opentelemetry.sdk.metrics._internal.aggregation import (
    ExplicitBucketHistogramAggregation,
)
from opentelemetry.sdk.metrics._internal.export import PeriodicExportingMetricReader
from opentelemetry.sdk.metrics._internal.view import View
from opentelemetry.sdk.resources import SERVICE_NAME, Resource
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import BatchSpanProcessor

if TYPE_CHECKING:
    from fastapi import FastAPI

    from eodag import EODataAccessGateway


logger = logging.getLogger("eodag.rest.utils.observability")


def create_tracer_provider(resource: Resource) -> Union[TracerProvider, trace.TracerProvider]:
    """create opentelemetry tracer provider"""
    tracer_provider = trace.get_tracer_provider()
    if tracer_provider and not isinstance(tracer_provider, trace.ProxyTracerProvider):
        logger.debug("Tracer provider already set, skipping creation.")
        return tracer_provider

    tracer_provider = TracerProvider(resource=resource)
    processor = BatchSpanProcessor(OTLPSpanExporter())
    tracer_provider.add_span_processor(processor)
    trace.set_tracer_provider(tracer_provider)
    return tracer_provider


def create_meter_provider(resource: Resource) -> Union[MeterProvider, metrics.MeterProvider]:
    """create opentelemetry meter provider"""
    meter_provider = metrics.get_meter_provider()
    if meter_provider and not isinstance(meter_provider, metrics._internal._ProxyMeterProvider):
        logger.debug("Meter provider already set, skipping creation.")
        return meter_provider

    reader = PeriodicExportingMetricReader(OTLPMetricExporter())
    view_histograms: View = View(
        instrument_type=metrics.Histogram,
        aggregation=ExplicitBucketHistogramAggregation(
            boundaries=(
                0.25,
                0.50,
                0.75,
                1.0,
                1.5,
                2.0,
                3.0,
                4.0,
                5.0,
                6.0,
                7.0,
                8.0,
                9.0,
                10.0,
            )
        ),
    )
    view_overhead_histograms: View = View(
        instrument_type=metrics.Histogram,
        instrument_name="*overhead*",
        aggregation=ExplicitBucketHistogramAggregation(
            boundaries=(
                0.030,
                0.040,
                0.050,
                0.060,
                0.070,
                0.080,
                0.090,
                0.100,
                0.125,
                0.150,
                0.175,
                0.200,
                0.250,
                0.500,
            )
        ),
    )
    meter_provider = MeterProvider(
        resource=resource,
        metric_readers=[reader],
        views=(
            view_histograms,
            view_overhead_histograms,
        ),
    )
    metrics.set_meter_provider(meter_provider)
    return meter_provider


def instrument_fastapi(
    fastapi_app: FastAPI,
) -> None:
    """Instrument FastAPI app."""
    logger.info("Instrument FastAPI app")
    resource = Resource(attributes={SERVICE_NAME: "stac-fastapi-eodag"})
    tracer_provider = create_tracer_provider(resource)
    meter_provider = create_meter_provider(resource)
    FastAPIInstrumentor.instrument_app(
        app=fastapi_app,
        tracer_provider=tracer_provider,
        meter_provider=meter_provider,
    )


def instrument_eodag(eodag_api: EODataAccessGateway):
    """Instrument EODAG app"""
    logger.info("Instrument EODAG app")
    resource = Resource(attributes={SERVICE_NAME: "stac-fastapi-eodag"})
    tracer_provider = create_tracer_provider(resource)
    meter_provider = create_meter_provider(resource)
    EODAGInstrumentor(eodag_api).instrument(
        tracer_provider=tracer_provider,
        meter_provider=meter_provider,
    )
