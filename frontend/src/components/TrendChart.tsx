import { Card } from "@/components/ui/card";
import { LineChart, Line, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer, Legend } from "recharts";

const defaultData = [
  { date: "Oct 1", mentions: 45, visibility: 72 },
  { date: "Oct 8", mentions: 52, visibility: 78 },
  { date: "Oct 15", mentions: 61, visibility: 82 },
  { date: "Oct 22", mentions: 58, visibility: 85 },
  { date: "Oct 29", mentions: 67, visibility: 88 },
  { date: "Nov 5", mentions: 73, visibility: 91 },
  { date: "Nov 12", mentions: 84, visibility: 94 },
];

interface TrendChartProps {
  data?: Array<{ date: string; value?: number; mentions?: number; visibility?: number; [key: string]: any }>;
}

export const TrendChart = ({ data = defaultData }: TrendChartProps) => {
  return (
    <Card className="p-6 h-full flex flex-col border border-border">
      <h3 className="text-lg font-semibold mb-4">Visibility Trends</h3>
      <div className="flex-1 min-h-[300px]">
        <ResponsiveContainer width="100%" height="100%">
          <LineChart data={data}>
            <CartesianGrid strokeDasharray="3 3" stroke="hsl(var(--border))" />
            <XAxis
              dataKey="date"
              stroke="hsl(var(--muted-foreground))"
              fontSize={12}
            />
            <YAxis
              stroke="hsl(var(--muted-foreground))"
              fontSize={12}
            />
            <Tooltip
              contentStyle={{
                backgroundColor: "hsl(var(--card))",
                border: "1px solid hsl(var(--border))",
                borderRadius: "var(--radius)",
              }}
            />
            <Legend />
            {data[0]?.value !== undefined && (
              <Line
                type="monotone"
                dataKey="value"
                stroke="hsl(var(--primary))"
                strokeWidth={3}
                dot={{ fill: "hsl(var(--primary))", r: 4 }}
                activeDot={{ r: 6 }}
              />
            )}
            {data[0]?.mentions !== undefined && (
              <Line
                type="monotone"
                dataKey="mentions"
                stroke="hsl(var(--primary))"
                strokeWidth={3}
                dot={{ fill: "hsl(var(--primary))", r: 4 }}
                activeDot={{ r: 6 }}
              />
            )}
            {data[0]?.visibility !== undefined && (
              <Line
                type="monotone"
                dataKey="visibility"
                stroke="hsl(var(--secondary))"
                strokeWidth={3}
                dot={{ fill: "hsl(var(--secondary))", r: 4 }}
                activeDot={{ r: 6 }}
              />
            )}
          </LineChart>
        </ResponsiveContainer>
      </div>
    </Card>
  );
};
