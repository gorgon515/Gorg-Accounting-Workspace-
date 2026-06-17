import { Page } from './_page';
import { Panel, StatusBadge, MetricCard } from '../components';

// N8N embedding is a Phase-2 roadmap item; the Automation agent + seam exist.
// This surface honestly reflects that state rather than faking workflow data.
export function Automations() {
  return (
    <Page title="Automation Center" subtitle="N8N workflows · AI-built automations"
      actions={<StatusBadge status="planned" label="N8N integration planned" />}>
      <div className="grid grid-cols-2 md:grid-cols-4 gap-3 mb-3">
        <MetricCard label="Workflows" value="—" sub="connect N8N" />
        <MetricCard label="Executions" value="—" />
        <MetricCard label="Failures" value="—" />
        <MetricCard label="Schedules" value="—" />
      </div>
      <Panel title="Natural-language workflow builder" subtitle="Automation Agent">
        <p className="text-[12px] text-warmgray leading-relaxed">
          The Automation Agent turns plain requests into N8N workflows — e.g.
          <span className="text-ivory"> "download invoice attachments from Gmail and file them by vendor"</span> or
          <span className="text-ivory"> "create a monthly accounting report workflow"</span>.
        </p>
        <p className="text-[12px] text-warmgray/70 mt-2 leading-relaxed">
          The orchestration seam is in place (the Automation agent is in the roster). Embedding the live
          N8N editor and the create/execute/monitor controls is the next automation milestone; this center
          will host the workflow browser, execution monitor, and AI builder once N8N is wired in.
        </p>
      </Panel>
    </Page>
  );
}
