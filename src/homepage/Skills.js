import React from "react";
import handleViewport from "react-in-viewport";
import {
  Card,
  CardBody,
  CardHeader,
  Col,
  Container,
  Progress,
  Row,
} from "reactstrap";
import skillsData from "./skills-data.json";

const FINDER_STRING_PATTERN = /(?:(lang|github):(.+)|url:(.+):(.+))/;

class URLProjectFinder {
  constructor(resourceLocation) {
    this.resourceLocation = resourceLocation;
  }
}

class LangProjectFinder {
  constructor(language) {
    this.language = language;
  }
}

function createProjectFinder(resource) {
  const match = resource.match(FINDER_STRING_PATTERN);
  if (!match) {
    throw new Error(`Finder ${resource} does not match pattern`);
  }
}

class SkillData {
  constructor(data) {
    this.name = data.name;
    this.skill = data.skill;
    this.projects = data.projects.map(createProjectFinder);
  }
}

class AnimatedSkillBarBlock extends React.Component {
  constructor(props) {
    super(props);
    const { value } = this.props;
    this.state = {
      displayed: 0,
      value: value,
    };
  }

  render() {
    const { value, displayed } = this.state;
    if (this.props.inViewport && value !== displayed) {
      this.setState({ displayed: value });
    }
    return <Progress value={displayed} />;
  }
}

function SkillInfoDisplay(props) {
  const { name, skill } = props.data;
  return (
    <Row>
      <Col md="4">
        <p>{name}</p>
      </Col>
      <Col md="7">
        <AnimatedSkillBar value={skill} />
      </Col>
      <Col sm="1">{/* projects dropdown goes here */}</Col>
    </Row>
  );
}

function CategoryCard(props) {
  const { children, skills } = props;
  return (
    <Card>
      <CardHeader>
        <h4>{children}</h4>
      </CardHeader>
      <CardBody>
        <Container>
          {skills
            .map((x) => new SkillData(x))
            .sort((a, b) => b.skill - a.skill)
            .map((x) => (
              <SkillInfoDisplay key={x.name} data={x} />
            ))}
        </Container>
      </CardBody>
    </Card>
  );
}

const AnimatedSkillBar = handleViewport(AnimatedSkillBarBlock, {
  rootMargin: "-1.0px",
});

function SkillsSection() {
  return (
    <section>
      <Container>
        <div className="section-header">
          <h2>Skills</h2>
        </div>
        <Row>
          <Col lg="6">
            <CategoryCard skills={skillsData.languages}>Languages</CategoryCard>
            <CategoryCard skills={skillsData.frontend}>Frontend</CategoryCard>
            <CategoryCard skills={skillsData.backend}>Backend</CategoryCard>
          </Col>
          <Col lg="6">
            <CategoryCard skills={skillsData.ee}>
              Electrical Engineering
            </CategoryCard>
            <CategoryCard skills={skillsData.data}>Data Science</CategoryCard>
            <CategoryCard skills={skillsData.games}>Game Engines</CategoryCard>
          </Col>
        </Row>
      </Container>
    </section>
  );
}

export { AnimatedSkillBar, SkillsSection };
