"use client";

import { useQuery } from "@tanstack/react-query";
import { analytics, campaigns } from "@/lib/api";
import { pct, formatDate } from "@/lib/utils";
import { useState } from "react";
import {
  BarChart, Bar, XAxis, YAxis, Tooltip, ResponsiveContainer, CartesianGrid,
} from "recharts";

export default function AnalyticsPage() {
  const [campaignId, setCampaignId] = useState("");

  const { data: campaignData } = useQuery({
    queryKey: ["campaigns"],
    queryFn: () => campaigns.list({ page_size: 100 }),
  });

  const { data: summary, isLoading } = useQuery({
    queryKey: ["analytics-summary", campaignId],
    queryFn: () => analytics.summary({ campaign_id: campaignId || undefined }),
  });

  const kpis = [
    { label: "Sends", value: summary?.total_sends ?? 0 },
    { label: "Opens", value: summary?.total_opens ?? 0 },
    { label: "Clicks", value: summary?.total_clicks ?? 0 },
    { label: "Conversions", value: summary?.total_conversions ?? 0 },
    { label: "Open Rate", value: pct(summary?.avg_open_rate ?? 0) },
    { label: "Click Rate", value: pct(summary?.avg_click_rate ?? 0) },
    { label: "Spend", value: `$${(summary?.total_spend ?? 0).toFixed(2)}` },
    { label: "Assets Generated", value: summary?.assets_generated ?? 0 },
  ];

  const chartData = summary?.by_channel?.map((c: any) => ({
    name: c.channel,
    Sends: c.sends,
    Opens: c.opens,
    Clicks: c.clicks,
    Conversions: c.conversions,
  })) ?? [];

  return (
    <div className="space-y-8">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-semibold">Analytics</h1>
          <p className="text-sm text-muted-foreground mt-1">
            Campaign funnel metrics and performance.
          </p>
        </div>
        <select
          className="input text-sm max-w-xs"
          value={campaignId}
          onChange={(e) => setCampaignId(e.target.value)}
        >
          <option value="">All campaigns</option>
          {campaignData?.items?.map((c: any) => (
            <option key={c.id} value={c.id}>{c.name}</option>
          ))}
        </select>
      </div>

      {/* KPI cards */}
      <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
        {kpis.map(({ label, value }) => (
          <div key={label} className="rounded-lg border border-border bg-card p-4">
            <div className="text-xs text-muted-foreground mb-1">{label}</div>
            <div className="text-2xl font-semibold">{isLoading ? "—" : value}</div>
          </div>
        ))}
      </div>

      {/* Channel breakdown chart */}
      {chartData.length > 0 && (
        <div className="rounded-lg border border-border p-4">
          <h2 className="text-sm font-medium mb-4">By Channel</h2>
          <ResponsiveContainer width="100%" height={240}>
            <BarChart data={chartData} margin={{ top: 0, right: 8, left: 0, bottom: 0 }}>
              <CartesianGrid strokeDasharray="3 3" className="stroke-border" />
              <XAxis dataKey="name" tick={{ fontSize: 12 }} />
              <YAxis tick={{ fontSize: 12 }} />
              <Tooltip />
              <Bar dataKey="Sends" fill="hsl(220.9 39.3% 11%)" radius={[2, 2, 0, 0]} />
              <Bar dataKey="Opens" fill="hsl(220 14.3% 60%)" radius={[2, 2, 0, 0]} />
              <Bar dataKey="Clicks" fill="hsl(220 8.9% 46.1%)" radius={[2, 2, 0, 0]} />
              <Bar dataKey="Conversions" fill="hsl(142 76% 36%)" radius={[2, 2, 0, 0]} />
            </BarChart>
          </ResponsiveContainer>
        </div>
      )}

      {chartData.length === 0 && !isLoading && (
        <div className="rounded-lg border border-dashed border-border py-16 text-center text-sm text-muted-foreground">
          No analytics events yet. Send a campaign to start tracking.
        </div>
      )}
    </div>
  );
}
